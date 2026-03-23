# Scribble for my initial thoughts / Claude first input

# Written using voice dictation tool, ignore punctuations and grammar.

So, yeah, based on the document and the coding assessment, the goal is to identify top contributors, top engineers who contribute the "best" for the repository. Please go through the "engineering impact assignment document" before evaluating my prompt/task. 

The first things that come to my mind are:
- basic counts and code contributions
- PRs, commits, lines of code, maybe file types
Then maybe generating a composite score for them, assigning weights to each contribution, creating a few graphs, and identifying top contributors that way. We can take it a bit further by also classifying different contributions and considering them. I don't believe in counts; I don't think the number of PRs, commits, and lines of code matter that much. The type of contribution they are making is also important, so just pure PRs, commits, and lines of code I'll probably skip, but I'll consider the counts of actual impactful contributions.

The next thing is, how do we identify an important, impactful contribution, right? 

These can be classified by what exactly is the contribution, by checking if it's:
- the actual code
- just documentation
- just configuration
- updating libraries
- something in the code, like a feature or an actual bug fix, contributing to something that is being fixed, which is high impact
We can have an LLM judge that. If it's a new feature, then obviously it's a huge impact, especially if it's a feature integrating with the existing system. I would prioritize code, backend, a lot more than the docs, configurations, updating libraries, and even minor bug fixes, which are not that important, like adding type constraints, which are potentially handled during runtime already by the code and just get added for code quality. That should not be a huge contribution.

Next, I would say, is the review quality as well. For me, a good engineer is also one who unblocks others as fast as possible and adds comments. Just approval, just looking at an engineer who responds the fastest to a particular issue, can be a minor metric as well, which is essentially an unblock rate for someone. Also, for the contributor, it can be how quickly they incorporate review comments in their code, if they are ignoring it, if they have never been worked upon. All those metrics can also go in the impact score. So essentially, a signal where PRs are, if someone has raised a PR and there are comments on it, how quickly they incorporate the feedback. 

Next can be something like purely technical: how many parts of the code they touch. If they cover all parts of it, like:
- front end
- back end
- side features
- database
- everything
Or if it's just one particular system that they're focusing on, like a more generalist engineer is more valuable than a specialist. Again, that is debatable. If the specialist engineer is essentially taking care of the entire feature, he is probably more important than a generalist who doesn't own anything. That is also one part of it.

So these are the thoughts I have. I do want to make it like this: I don't believe in static weighted scores. I would prefer for an LLM to take this over first for the implementation and thinking of data collection, and then we can build a script or system which generates the scores for the data and prepares the results. This can be our actual statistics that we want to use.  
  
There is a separate application or the front end part which displays the output that is saved in the same file and then uses it on the front page to show the statistics. That's the architecture that I'm thinking. Essentially, we are doing two things:

1. A Python or backend-based evaluator which possibly can read input and give out output.
2. Input/Data gatherer: how to fetch the input data from github, I don't know, GitHub APIs or scraper. I will leave that upto youl. We can target data from the last 30 days to keep it simple. And the final output: we can save these statistics somewhere and then evaluate Python-based again. I guess I'm open to it, which possibly has an evaluator that can generate an output file which are essentially statistics for the data that we have. We can use an algorithm behind it, or I'm okay creating an algorithm, but I would prefer not to do that just to have something more robust. I think having an LLM judge is better, so that's one.

The third part, or the last part, is a front end which uses the output from the evaluator and shows the statistics on the main page, which will deploy it on Vercel. 

So this is what I'm thinking. Let's chat. 

Architecture: 
1 Python for Data scraping and evaluation
2 Frontend next.js to show data on vercel deployment

Keep it simple. Don't overcomplicate it. Follow the assignments instructions as well (things llike frontend page is 1 page only, clear understandable metrics shown, fast loading UI (Fast loading is not a problem with us as we're using downloaded data)
