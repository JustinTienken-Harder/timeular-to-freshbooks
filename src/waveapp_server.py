"""
Flask Web Application for WaveApp Invoice Generation

Multi-step workflow:
1. Upload CSV
2. Match activities to customers and tags to services
3. Preview invoices
4. Generate invoices in WaveApp
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from werkzeug.utils import secure_filename

from waveapps.client import WaveAppClient
from waveapps.csv_processor import TimeularCSVProcessor
from waveapps.models import Invoice, InvoiceItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'flask_session')
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure server-side sessions to avoid cookie size limits
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = SESSION_FOLDER
app.config['SESSION_PERMANENT'] = False
Session(app)

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Initialize WaveApp client (will be None if credentials not set)
waveapp_client = None
try:
    api_token = os.getenv('WAVEAPP_API_TOKEN')
    business_id = os.getenv('WAVEAPP_BUSINESS_ID')
    
    if api_token and business_id:
        waveapp_client = WaveAppClient(api_token, business_id)
        logger.info("WaveApp client initialized successfully")
    else:
        logger.warning("WaveApp credentials not found in environment variables")
except Exception as e:
    logger.error(f"Failed to initialize WaveApp client: {e}")


def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page with CSV upload form"""
    # Clear any existing session data
    session.clear()
    return render_template('waveapp/upload.html')


@app.route('/upload', methods=['POST'])
def upload_csv():
    """Handle CSV file upload and processing"""
    if not waveapp_client:
        flash('WaveApp client not configured. Please check environment variables.', 'error')
        return redirect(url_for('index'))
    
    # Check if file was uploaded
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Saved file to: {filepath}")
        
        # Process CSV
        processor = TimeularCSVProcessor(filepath)
        processed_data = processor.process()
        
        logger.info(f"Processing complete. Activities: {len(processed_data)}")
        
        # Store in session
        session['csv_filepath'] = filepath
        session['processed_data'] = processed_data
        session['summary'] = processor.get_summary()
        
        logger.info(f"Processed CSV: {processor.get_summary()}")
        flash(f"Successfully processed {len(processed_data)} activities", 'success')
        
        return redirect(url_for('match'))
        
    except Exception as e:
        import traceback
        logger.error(f"Error processing CSV: {e}")
        logger.error(traceback.format_exc())
        flash(f"Error processing CSV: {str(e)}", 'error')
        return redirect(url_for('index'))


@app.route('/match')
def match():
    """Display matching interface for activities and tags"""
    if 'processed_data' not in session:
        flash('No data to process. Please upload a CSV file first.', 'warning')
        return redirect(url_for('index'))
    
    try:
        # Get processed data
        processed_data = session['processed_data']
        
        # Get unique activities and tags
        activities = list(processed_data.keys())
        tags = set()
        for activity_data in processed_data.values():
            tags.update(activity_data['entries_by_tag'].keys())
        tags = sorted(list(tags))
        
        # Fetch WaveApp customers and products
        customers = waveapp_client.get_customers()
        products = waveapp_client.get_products()
        
        return render_template(
            'waveapp/match.html',
            activities=activities,
            tags=tags,
            customers=customers,
            products=products,
            processed_data=processed_data,
            summary=session.get('summary', {})
        )
        
    except Exception as e:
        logger.error(f"Error in match route: {e}")
        flash(f"Error loading matching page: {str(e)}", 'error')
        return redirect(url_for('index'))


@app.route('/submit-mappings', methods=['POST'])
def submit_mappings():
    """Handle user's activity→customer and tag→service mappings"""
    if 'processed_data' not in session:
        flash('Session expired. Please upload CSV again.', 'warning')
        return redirect(url_for('index'))
    
    try:
        # Get form data
        form_data = request.form.to_dict()
        
        # Parse activity mappings (format: activity_<activity_name>)
        activity_mappings = {}
        for key, value in form_data.items():
            if key.startswith('activity_') and value:
                activity_name = key[9:]  # Remove 'activity_' prefix
                activity_mappings[activity_name] = value
        
        # Parse tag mappings (format: tag_<tag_name>)
        tag_mappings = {}
        for key, value in form_data.items():
            if key.startswith('tag_') and value:
                tag_name = key[4:]  # Remove 'tag_' prefix
                tag_mappings[tag_name] = value
        
        # Validate all required mappings are present
        processed_data = session['processed_data']
        activities = list(processed_data.keys())
        tags = set()
        for activity_data in processed_data.values():
            tags.update(activity_data['entries_by_tag'].keys())
        
        missing_activities = [act for act in activities if act not in activity_mappings]
        missing_tags = [tag for tag in tags if tag not in tag_mappings]
        
        if missing_activities or missing_tags:
            error_msg = []
            if missing_activities:
                error_msg.append(f"Missing customer mappings for: {', '.join(missing_activities)}")
            if missing_tags:
                error_msg.append(f"Missing service mappings for: {', '.join(missing_tags)}")
            flash(' '.join(error_msg), 'error')
            return redirect(url_for('match'))
        
        # Store mappings in session
        session['activity_mappings'] = activity_mappings
        session['tag_mappings'] = tag_mappings
        
        logger.info(f"Saved mappings: {len(activity_mappings)} activities, {len(tag_mappings)} tags")
        return redirect(url_for('preview'))
        
    except Exception as e:
        logger.error(f"Error submitting mappings: {e}")
        flash(f"Error processing mappings: {str(e)}", 'error')
        return redirect(url_for('match'))


@app.route('/preview')
def preview():
    """Preview invoices before generation"""
    required_keys = ['processed_data', 'activity_mappings', 'tag_mappings']
    if not all(key in session for key in required_keys):
        flash('Missing data. Please start from the beginning.', 'warning')
        return redirect(url_for('index'))
    
    try:
        processed_data = session['processed_data']
        activity_mappings = session['activity_mappings']
        tag_mappings = session['tag_mappings']
        
        # Get customers and products for display
        customers = {c.id: c for c in waveapp_client.get_customers()}
        products = {p.id: p for p in waveapp_client.get_products()}
        
        # Build invoice preview data
        invoices_preview = []
        
        for activity, activity_data in processed_data.items():
            customer_id = activity_mappings.get(activity)
            if not customer_id:
                continue
            
            customer = customers.get(customer_id)
            if not customer:
                continue
            
            # Build line items
            line_items = []
            invoice_total = 0.0
            
            for tag, tag_data in activity_data['entries_by_tag'].items():
                product_id = tag_mappings.get(tag)
                if not product_id:
                    continue
                
                product = products.get(product_id)
                if not product:
                    continue
                
                hours = tag_data['hours']
                notes = tag_data['notes']
                line_total = product.price * hours
                invoice_total += line_total
                
                line_items.append({
                    'product_name': product.name,
                    'quantity': hours,
                    'rate': product.price,
                    'notes': notes,
                    'total': line_total
                })
            
            if line_items:
                invoices_preview.append({
                    'customer_name': customer.name,
                    'customer_email': customer.email,
                    'line_items': line_items,
                    'total': invoice_total
                })
        
        return render_template(
            'waveapp/preview.html',
            invoices=invoices_preview,
            total_invoices=len(invoices_preview)
        )
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        flash(f"Error generating preview: {str(e)}", 'error')
        return redirect(url_for('match'))


@app.route('/generate', methods=['POST'])
def generate_invoices():
    """Generate invoices in WaveApp"""
    required_keys = ['processed_data', 'activity_mappings', 'tag_mappings']
    if not all(key in session for key in required_keys):
        flash('Missing data. Please start from the beginning.', 'warning')
        return redirect(url_for('index'))
    
    try:
        processed_data = session['processed_data']
        activity_mappings = session['activity_mappings']
        tag_mappings = session['tag_mappings']
        
        created_invoices = []
        errors = []
        
        # Create invoices for each activity
        for activity, activity_data in processed_data.items():
            customer_id = activity_mappings.get(activity)
            if not customer_id:
                errors.append(f"No customer mapping for {activity}")
                continue
            
            # Build line items
            items = []
            for tag, tag_data in activity_data['entries_by_tag'].items():
                product_id = tag_mappings.get(tag)
                if not product_id:
                    errors.append(f"No service mapping for tag '{tag}' in {activity}")
                    continue
                
                item = InvoiceItem(
                    product_id=product_id,
                    quantity=tag_data['hours'],
                    description=tag_data['notes']
                )
                items.append(item)
            
            if not items:
                errors.append(f"No valid line items for {activity}")
                continue
            
            # Create invoice
            invoice = Invoice(
                customer_id=customer_id,
                items=items,
                invoice_date=datetime.now()
            )
            
            try:
                created_invoice = waveapp_client.create_invoice(invoice)
                created_invoices.append({
                    'activity': activity,
                    'invoice_number': created_invoice.invoice_number,
                    'total': created_invoice.total,
                    'view_url': created_invoice.view_url
                })
                logger.info(f"Created invoice {created_invoice.invoice_number} for {activity}")
            except Exception as e:
                error_msg = f"Failed to create invoice for {activity}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Store results in session
        session['created_invoices'] = created_invoices
        session['errors'] = errors
        
        if created_invoices:
            flash(f"Successfully created {len(created_invoices)} invoice(s)", 'success')
        if errors:
            flash(f"{len(errors)} error(s) occurred", 'warning')
        
        return redirect(url_for('success'))
        
    except Exception as e:
        logger.error(f"Error generating invoices: {e}")
        flash(f"Error generating invoices: {str(e)}", 'error')
        return redirect(url_for('preview'))


@app.route('/success')
def success():
    """Display success page with created invoices"""
    if 'created_invoices' not in session:
        flash('No invoices to display', 'warning')
        return redirect(url_for('index'))
    
    created_invoices = session.get('created_invoices', [])
    errors = session.get('errors', [])
    
    return render_template(
        'waveapp/success.html',
        invoices=created_invoices,
        errors=errors
    )


# API endpoints for AJAX calls
@app.route('/api/customers')
def api_customers():
    """Return customers as JSON"""
    try:
        customers = waveapp_client.get_customers(force_refresh=True)
        return jsonify([
            {'id': c.id, 'name': c.name, 'email': c.email}
            for c in customers
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/products')
def api_products():
    """Return products as JSON"""
    try:
        products = waveapp_client.get_products(force_refresh=True)
        return jsonify([
            {'id': p.id, 'name': p.name, 'price': p.price, 'description': p.description}
            for p in products
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run in debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5001)
