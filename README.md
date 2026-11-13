## Welcome to Haoyi Xiong's Page

Dr. Haoyi Xiong currently a principal R&D architect and the mannger of Big Data Lab, Baidu Research. From Fall 2016 to Spring 2018, He was a Tenure Track Assistant Professor in Department of Computer Science, Missouri University of Science and Technology, Rolla, Missouri. Before that He was a Postdoctoral Research Associate in Department of Systems and Information Engineering, University of Virginia, Charlottesville, Virginia. He received Ph.D degree in Computer Science from Telecom SudParis jointly with Pierre and Marie Curie University, Paris, France in 2015. He obtained M.Sc and B.Eng degrees from the Hong Kong University of Science and Technology (2010) and Huazhong University of Science and Technology (2009), respectively.

## Scholar metrics in the hero

`assets/scholar-metrics.json` holds the last verified all-time citations,
h-index, and i10-index for the public Scholar profile. The hero reads it on
load and keeps the values baked into `index.html` when the fetch fails.

Refresh locally (works from a normal network):

```bash
python scripts/update_scholar_metrics.py
```

The daily workflow runs the same script, but Google returns 403 to GitHub's
data-center IPs. It therefore exits green without changing the file and keeps
the last values. To refresh from CI, add a `SERPAPI_API_KEY` repository secret;
the script then reads the same three values through SerpAPI's Scholar Author
engine. No paper count is stored or displayed.
