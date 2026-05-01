# COMP3011 Coursework 2: Search Engine Tool

## Project overview and purpose

This project implements a Python command-line search tool for COMP3011 Web Services and Web Data Coursework 2.

The tool:
- crawls `https://quotes.toscrape.com/`
- respects a 6-second politeness window between requests
- builds an inverted index of words found in crawled pages
- stores per-page word statistics including frequency and positions
- saves and loads the compiled index from disk
- supports command-line search operations for printing one term and finding multi-word queries
- ranks matches using TF-IDF-inspired scoring
- supports positional phrase search such as `find "good friends"`
- suggests corrected query terms for close misspellings

## Feature summary

- Polite breadth-first crawl of the target quote pages only
- Canonical URL handling so the home page and `/page/1/` are not indexed twice
- Case-insensitive tokenisation with apostrophe-aware word handling
- Positional inverted index with per-page frequency and token positions
- Persistent compiled index stored in `data/index.json`
- Exact phrase search built on positional postings
- Query suggestion support for close misspellings
- Automated test workflow through GitHub Actions
- Benchmark script for representative search queries

## Repository structure

```text
repository-name/
src/
  crawler.py
  indexer.py
  search.py
  main.py
tests/
  test_crawler.py
  test_indexer.py
  test_search.py
data/
  index.json
requirements.txt
README.md
```

## Installation/setup instructions

1. Ensure Python 3.11 or later is available.
2. Create and activate a virtual environment.
3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run commands from the repository root.

## Usage examples

The tool supports both direct command execution and an interactive shell.

### Direct commands

```bash
python src/main.py build
python src/main.py load
python src/main.py print nonsense
python src/main.py find good friends
python src/main.py find "good friends"
python src/main.py find godo frends
```

### Interactive shell

Start the shell:

```bash
python src/main.py
```

Then enter commands such as:

```text
> build
> load
> print nonsense
> find good friends
> find "good friends"
> find godo frends
```

### Command summary

- `build`
  Crawls the target website, builds the inverted index, and saves it to `data/index.json`.
- `load`
  Loads the saved index from `data/index.json`.
- `print <word>`
  Prints the inverted-index entry for a single word.
- `find <query terms>`
  Returns pages containing all supplied search terms, ranked by TF-IDF-inspired scoring.

## Example behaviour

### Single-word lookup

```bash
python src/main.py print good
```

### Multi-word AND query

```bash
python src/main.py find good friends
```

### Exact phrase query

```bash
python src/main.py find "good friends"
```

### Query suggestion

```bash
python src/main.py find godo frends
```

If no exact match is found but a close query exists in the vocabulary, the shell returns a suggestion.

## Architecture and design

### `src/crawler.py`

Responsible for:
- crawling the target website with breadth-first traversal
- filtering links to the quote listing pages only
- enforcing the 6-second politeness window
- returning canonical page data for indexing

### `src/indexer.py`

Responsible for:
- tokenising page text
- normalising words to lowercase
- building the inverted index
- storing per-page frequency and token positions

### `src/search.py`

Responsible for:
- loading and saving the compiled index
- returning postings for `print`
- resolving AND queries for `find`
- evaluating exact phrase matches through positional postings
- ranking matches with TF-IDF-inspired scoring
- suggesting close query alternatives

### `src/main.py`

Responsible for:
- command-line command dispatch
- interactive shell support
- user-facing error handling and output

## Search and ranking approach

The implementation uses a positional inverted index. Each term maps to pages containing that term, and each page stores:
- `frequency`
- `positions`

This design supports:
- fast single-term lookup
- AND query intersection
- exact phrase search through position alignment
- ranking based on a standard information-retrieval idea: TF-IDF

The current ranking function combines:
- log-scaled term frequency
- inverse document frequency
- a small bonus for exact phrase matches

## Complexity discussion

Let:
- `N` be the number of crawled pages
- `T` be the number of total tokens across all pages
- `df(t)` be the document frequency of term `t`

### Build phase

- Crawling is proportional to the number of fetched pages and extracted links.
- Index construction is `O(T)` because each token is processed once.

### Search phase

- `print <word>` is effectively `O(1)` average-time dictionary lookup, excluding output size.
- `find` first narrows candidate documents through postings intersection.
- Exact phrase queries add position alignment work over candidate pages.
- TF-IDF scoring is proportional to the number of matched pages for the query.

For this coursework dataset, these operations are comfortably fast, but the design also mirrors the core ideas used in larger search systems.

## Testing instructions

Run the test suite with:

```bash
pytest
```

To run the same checks with verbose output:

```bash
pytest -v
```

The GitHub Actions pipeline runs:

```bash
pytest -v --cov=src --cov-report=term-missing --cov-fail-under=95
```

This enforces coverage on the main code under `src/`.

## Benchmarking

Run the benchmark script against the compiled index with:

```bash
python3 scripts/benchmark_search.py --iterations 100
```

This benchmarks representative queries such as:
- `life`
- `good friends`
- `be yourself`
- `truth`
- `happiness`

The benchmark is intended to provide repeatable evidence for search responsiveness and support discussion of performance in the video demonstration.

## Dependencies

- `requests`
- `beautifulsoup4`
- `pytest`
- `pytest-cov`

Install all dependencies with:

```bash
pip install -r requirements.txt
```

## Development workflow

The repository was developed incrementally using:
- dedicated branches for setup, crawler, indexing, storage, search, and polish work
- regular commits with meaningful messages
- automated testing before merges into `main`

## Limitations

- The project is intentionally focused on the target coursework website rather than arbitrary web domains.
- The ranking model is lightweight and suitable for the coursework scale rather than a production web-scale engine.
- Query suggestions are close-match based, not dictionary- or language-model based.
