# WaveApp Integration - Action Plan

## Overview
Create a Flask-based browser application to upload Timeular CSV timesheets and generate WaveApp invoices. Users will upload CSV files, and the system will consolidate time entries by client (Activity) and service (Tags), allowing user-driven matching of activities to WaveApp clients and services.

---

## Architecture Components

### 1. **WaveApp API Client** (`src/waveapps/client.py`)
   - **Purpose**: Core API connector for WaveApp GraphQL API
   - **Pattern**: Similar to `src/freshbooks/client.py` structure
   - **Responsibilities**:
     - GraphQL query/mutation execution
     - Authentication with API token
     - Fetch customers (clients)
     - Fetch products/services
     - Create invoices with line items
     
### 2. **WaveApp Models** (`src/waveapps/models.py`)
   - **Purpose**: Data structures for WaveApp entities
   - **Models Needed**:
     - `Customer` (client entity)
     - `Product` (service entity)
     - `Invoice`
     - `InvoiceItem` (line item)
     
### 3. **CSV Processing Module** (`src/waveapps/csv_processor.py`)
   - **Purpose**: Transform Timeular CSV into grouped invoice data
   - **Responsibilities**:
     - Parse uploaded CSV files
     - Group entries by Activity (client)
     - Aggregate time by Tag (service) within each client
     - **Aggregate notes**: Concatenate all notes from individual time entries for each service/tag grouping
     - Calculate total hours (quantity) per service - **WaveApp will auto-calculate price based on ProductId × quantity**
     - Handle billable/non-billable filtering
     - **Do NOT use HourlyRate from CSV** - pricing comes from WaveApp Product definitions

### 4. **Flask Web Application** (`src/waveapp_server.py`)
   - **Purpose**: Browser-based interface for the integration
   - **Routes**:
     - `GET /` - Home page with CSV upload form
     - `POST /upload` - Handle CSV upload, process and display grouped data
     - `GET /clients` - Fetch WaveApp customers (AJAX)
     - `GET /services` - Fetch WaveApp products (AJAX)
     - `POST /match` - User submits activity→client and tag→service mappings
     - `POST /generate-invoices` - Create invoices in WaveApp
     - `GET /success` - Confirmation page
     
### 5. **Frontend Templates** (`src/templates/waveapp/`)
   - **Templates Needed**:
     - `upload.html` - CSV upload interface
     - `match.html` - Interactive matching UI (dropdowns/search)
     - `preview.html` - Review invoices before sending
     - `success.html` - Confirmation with invoice links
     
### 6. **Static Assets** (`src/static/waveapp/`)
   - **Files**:
     - `styles.css` - Custom styling
     - `app.js` - AJAX calls, dynamic dropdowns, form validation

---

## Detailed Implementation Steps

### Phase 1: WaveApp API Integration
**Files to Create:**
- `src/waveapps/client.py`
- `src/waveapps/models.py`

**Tasks:**
1. ✅ Create `WaveAppClient` class with GraphQL methods
   - `__init__(api_token, business_id)` - Initialize with credentials
   - `_execute_query(query, variables)` - GraphQL executor
   - `get_customers()` - Fetch all customers
   - `get_products()` - Fetch all products/services
   - `create_invoice(customer_id, line_items, invoice_date)` - Create invoice
   
2. ✅ Define data models in `models.py`
   - `Customer(id, name, email)`
   - `Product(id, name, price, description)` - price stored for reference only
   - `Invoice(customer_id, items, date, total)`
   - `InvoiceItem(product_id, quantity, description)` - **quantity = hours, WaveApp auto-calculates total from ProductId**
   - **Note**: description field should contain aggregated notes from all time entries for that service

3. ✅ Environment variables setup
   - Add to `.env`:
     ```
     WAVEAPP_API_TOKEN=your_token_here
     WAVEAPP_BUSINESS_ID=your_business_id
     ```

### Phase 2: CSV Processing Logic
**File to Create:**
- `src/waveapps/csv_processor.py`

**Tasks:**
1. ✅ Create `TimeularCSVProcessor` class
   - `load_csv(file_path)` - Parse CSV using pandas
   - `filter_billable()` - Keep only billable entries
   - `group_by_activity()` - Group by Activity (client)
   - `aggregate_by_tags()` - Sum hours per Tag within each Activity
   - `aggregate_notes()` - **Concatenate all Note fields for entries with same Activity+Tag**
   - **Remove `calculate_amounts()`** - WaveApp handles pricing automatically via ProductId
   
2. ✅ Output structure:
   ```python
   {
       "GulfCoast-HEART": {
           "total_hours": 15.5,
           "entries_by_tag": {
               "consulting:remote": {
                   "hours": 5,  # This becomes 'quantity' in invoice line item
                   "notes": "Call from Hana to troubleshoot... | Additional work on system setup..."  # Aggregated notes
               },
               "": {
                   "hours": 10.5,
                   "notes": "Meeting with client | Follow-up email correspondence"
               }
           }
       },
       "Integrative Body Massage": { ... }
   }
   ```
   **Note**: No `amount` or `rate` fields - WaveApp calculates using ProductId pricing

### Phase 3: Flask Application Setup
**File to Create:**
- `src/waveapp_server.py`

**Tasks:**
1. ✅ Initialize Flask app with:
   - File upload handling (configure `UPLOAD_FOLDER`)
   - Session management for multi-step workflow
   - Error handling middleware
   
2. ✅ Implement core routes:
   - `GET /` → Render upload form
   - `POST /upload` → Process CSV, store in session, redirect to matching
   - `GET /match` → Display activities/tags with dropdown menus
   - `POST /match` → Save user mappings to session
   - `GET /preview` → Show final invoice preview
   - `POST /generate` → Create invoices via WaveApp API
   - `GET /success` → Display results

3. ✅ Integration points:
   - Load `WaveAppClient` on app startup
   - Pre-fetch customers and products for dropdown population
   - Store processed CSV data in Flask session

### Phase 4: Frontend Development
**Files to Create:**
- `src/templates/waveapp/base.html` (base template)
- `src/templates/waveapp/upload.html`
- `src/templates/waveapp/match.html`
- `src/templates/waveapp/preview.html`
- `src/templates/waveapp/success.html`
- `src/static/waveapp/styles.css`
- `src/static/waveapp/app.js`

**Tasks:**
1. ✅ `upload.html`:
   - File input for CSV upload
   - Date range display (from CSV metadata)
   - Submit button to process file
   
2. ✅ `match.html`:
   - Table showing all unique Activities (unmapped clients)
   - Searchable dropdown to select WaveApp Customer for each Activity
   - Table showing all unique Tags (unmapped services)
   - Searchable dropdown to select WaveApp Product for each Tag
   - Form validation to ensure all required mappings are complete
   
3. ✅ `preview.html`:
   - Display invoices grouped by customer
   - Show line items with:
     - Service name (from WaveApp Product mapping)
     - Hours (quantity)
     - **Aggregated notes** from all time entries for that service
     - **Rate and amount** fetched from WaveApp Product (for display only - actual calculation happens in WaveApp)
   - Edit capability (back button)
   - Confirm button to generate invoices
   
4. ✅ `success.html`:
   - List of created invoices with WaveApp links
   - Download summary report option
   - Start over button

5. ✅ JavaScript (`app.js`):
   - Implement searchable/filterable dropdowns
   - AJAX calls to fetch fresh customer/service lists
   - Client-side validation before form submission
   - Loading states during API calls

### Phase 5: Testing & Integration
**Files to Create:**
- `tests/test_waveapp_client.py`
- `tests/test_csv_processor.py`

**Tasks:**
1. ✅ Unit tests for CSV processor
   - Test grouping logic (by Activity and Tag)
   - Test billable filtering
   - **Test note aggregation** - verify all notes are concatenated properly
   - Test hours summation per service
   
2. ✅ Integration tests for WaveApp client
   - Mock GraphQL responses
   - Test customer/product fetching
   - Test invoice creation
   
3. ✅ End-to-end manual testing
   - Upload sample CSV
   - Map activities and services
   - Generate test invoices in WaveApp sandbox

### Phase 6: Documentation & Deployment
**Tasks:**
1. ✅ Update `README.md` with:
   - WaveApp setup instructions
   - How to obtain API token
   - Usage workflow documentation
   
2. ✅ Add configuration guide:
   - Environment variables
   - CSV format requirements
   - Troubleshooting common issues

3. ✅ Deployment checklist:
   - Update `pyproject.toml` dependencies (add `graphql-core` if needed)
   - Create `.env.example` template
   - Set up production WSGI server (gunicorn)

---

## Key Design Decisions

### 1. **No Automatic Matching**
   - User explicitly maps activities → customers
   - User explicitly maps tags → services
   - Prevents incorrect invoice generation
   
### 2. **Session-Based Workflow**
   - Upload → Process → Match → Preview → Generate
   - Each step stores state in Flask session
   - Allows back/forward navigation
   
### 3. **Aggregation Strategy**
   - Primary grouping: By Activity (client)
   - Secondary grouping: By Tag (service)
   - **Sum hours** (becomes `quantity` field for invoice line items)
   - **Concatenate notes** from all time entries in each service grouping (separated by " | " or newlines)
   - **Pricing**: WaveApp automatically calculates line item total using `ProductId` × `quantity`
   - **Do NOT use Timeular HourlyRate** - WaveApp Product pricing is authoritative
   - One invoice per client, multiple line items per service

### 4. **CSV Format Expectations**
   Based on `uploads/2025-03-01_2025-03-10_report.csv`:
   - Required columns: `Activity`, `Duration`, `HourlyRate`, `Tags`, `Billable`
   - Duration format: `HH:MM:SS`
   - Billable: "yes" or empty/no
   - Tags: comma-separated or single value

---

## Dependencies to Add

```toml
# Add to pyproject.toml dependencies
"flask>=3.1.0",  # Already present
"pandas>=2.2.3",  # Already present
"requests>=2.26.0",  # Already present
```

No additional dependencies needed - GraphQL can be handled with plain `requests`.

---

## File Structure After Implementation

```
src/
├── waveapps/
│   ├── __init__.py
│   ├── client.py           # WaveApp API client (GraphQL)
│   ├── models.py           # Data models (Customer, Product, Invoice)
│   └── csv_processor.py    # CSV parsing and aggregation logic
├── templates/
│   └── waveapp/
│       ├── base.html
│       ├── upload.html
│       ├── match.html
│       ├── preview.html
│       └── success.html
├── static/
│   └── waveapp/
│       ├── styles.css
│       └── app.js
├── waveapp_server.py       # Flask application
└── main.py                 # Keep existing for FreshBooks

tests/
├── test_waveapp_client.py
└── test_csv_processor.py
```

---

## WaveApp API Resources

### Authentication
- API Token in headers: `Authorization: Bearer YOUR_TOKEN`

### Key GraphQL Queries/Mutations

**Fetch Customers:**
```graphql
query {
  business(id: "BUSINESS_ID") {
    customers {
      edges {
        node {
          id
          name
          email
        }
      }
    }
  }
}
```

**Fetch Products:**
```graphql
query {
  business(id: "BUSINESS_ID") {
    products {
      edges {
        node {
          id
          name
          defaultSellPrice
          description
        }
      }
    }
  }
}
```

**Create Invoice:**
```graphql
mutation CreateInvoice($input: InvoiceCreateInput!) {
  invoiceCreate(input: $input) {
    invoice {
      id
      invoiceNumber
      total
      viewUrl
    }
  }
}
```

---

## Workflow Summary

1. **User uploads CSV** → Server parses and groups data
2. **System displays unique activities and tags** → User maps to WaveApp entities
3. **System generates preview** → User reviews invoices
4. **User confirms** → System creates invoices via WaveApp API
5. **Success page** → Display created invoice links

---

## Next Steps

1. Start with Phase 1 (WaveApp API Client)
2. Test API connectivity with WaveApp
3. Implement CSV processing (Phase 2)
4. Build Flask app incrementally (Phase 3)
5. Add frontend last (Phase 4)
6. Test thoroughly (Phase 5)

---

## Notes
- Keep existing FreshBooks integration intact (`src/main.py`, `src/freshbooks/`)
- WaveApp integration is standalone
- Reuse CSV handling patterns from `src/timeular/csv_handler.py`
- Follow Flask patterns from `src/freshbooks/authentication.py` (already has Flask routes)

## Critical Implementation Details

### 🔴 Pricing Logic
- **WaveApp calculates prices automatically**: When creating invoice line items with a `productId` and `quantity`, WaveApp multiplies the product's `defaultSellPrice` by the quantity
- **Ignore Timeular HourlyRate**: The CSV's HourlyRate field has discrepancies and should NOT be used
- **Quantity = Total Hours**: For each service (Tag), sum all hours from individual time entries
- **Single source of truth**: WaveApp Product/Service definitions contain the authoritative pricing

### 📝 Note Aggregation
- **Concatenate all notes**: For each Activity+Tag combination, combine all Note fields from individual time entries
- **Format**: Separate notes with " | " or newlines for readability
- **Empty notes**: Handle gracefully (skip empty notes in concatenation)
- **Purpose**: Provides detailed description of work performed for that service on the invoice line item
- **Example**: 
  ```
  Time Entry 1: "Call with client about requirements"
  Time Entry 2: "Follow-up email with proposal"
  Time Entry 3: "Meeting to review mockups"
  
  Aggregated: "Call with client about requirements | Follow-up email with proposal | Meeting to review mockups"
  ```
