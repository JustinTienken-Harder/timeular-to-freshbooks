# Vibe Coding

I recently worked on a project for my mom to integrate her timeular - a time tracking software that allows you to sort what time you track by folders, activities, billable/unpaid, and more - with her freshbooks software. This should be a few simple API calls to timeular, convert the data to what freshbooks wants, and send it off to freshbooks. So, I gave vibe coding a try. A recently popularized form of "coding" that utilizes all LLM coding models to write *everything*. 

Turns out, like many projects, there's more complications -- missing data fields, OAuth2 authentication, having to whip up a flask server to perform authentication, and more.

But embrace the chaos, exponential code, poor design, recursion with hundreds of calls to functions. Here's some insights:

### The Good

Before the very impressive coding models -- the errors in LLM generate code are subtle. Hallucinating packages. Utilizing functions that don't exist. The code "looks" like something that someone would write, but doesn't actually work. The best usages was for code-completion, an amazing LSP. Something below:

```{python}
reversed_keys = {v, k for k ---}
```

Now you can start an entire project with a well tuned natural language prompt and the results... kind of work, and kinda looks not bad.

You can prompt fixes to bugs and get results that work, and not doubling down on trash approaches.

You can add new features that don't always break everything.

You can fit large swaths of code into the (now) huge context lengths.

The docstrings written are great.

The type hints are nearly free.

The time in to lines of code out are immense. 

Dump entire documentation pages in, get code that integrates out.


### The bad

The results are impressive from a purely "I can't believe next token prediction can take us this far" standpoint. But there is a lot left to be desired from the results thusfar from a usability, maintainability, and overall quality standpoint. Be blown away by what can be written. Be nervous at the results that mostly work.

- No care for effeciency of code
- Classes created do everything and the kitchen sink
- Can take seconds to write thousands of lines of code
- Grows unmanagable quick
- Reuses the same function... by rewriting that function every time. 
- Error handling is aweful.
- Reviewing wild code.
- Quantity over quality all the way down.



### Overall

Vibe coding looks like building a dreamweaver website. If you don't know what's under the hood, in the long-term you're going to be in trouble. The results of Claude 3.7 are the coding equivalent to the image results of stable diffusion (not from an architecture perspective). You can't help but be impressed, but also it's extremely peculiar.

If you visualized a "A blue colored red panda eating ice cream inside of a bowling alley with three astronauts", then you'd find the results visually stunning and highly unusual.



INSERT IMAGE HERE

In the realm of machine learning things get even more dicey. Would I trust an LLM to interpret the training/test loss graphs of a statistical model? No chance. Data preprocessing, data validation, cleaning, munging, or training loops with custom loss schedulers -- I don't think ever. But I wouldn't be surprised if it produces "reasonable" looking scripts for training a model and processing data.


You can take a look at the project over here (LINK TO REPOSITORY).