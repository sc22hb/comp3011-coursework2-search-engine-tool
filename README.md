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
```

### Command summary

- `build`
  Crawls the target website, builds the inverted index, and saves it to `data/index.json`.
- `load`
  Loads the saved index from `data/index.json`.
- `print <word>`
  Prints the inverted-index entry for a single word.
- `find <query terms>`
  Returns pages containing all supplied search terms.

## Testing instructions

Run the test suite with:

```bash
pytest
```

To run the same checks with verbose output:

```bash
pytest -v
```

## Dependencies

- `requests`
- `beautifulsoup4`
- `pytest`
- `pytest-cov`

Install all dependencies with:

```bash
pip install -r requirements.txt
```
