# COMP3011 Coursework 2: Search Engine Tool

## Project overview and purpose

This project implements a Python command-line search tool for COMP3011 Web Services and Web Data Coursework 2. The tool will crawl `https://quotes.toscrape.com/`, build an inverted index, persist that index, and allow command-line search over the crawled pages.

## Installation/setup instructions

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage examples

The final tool will support the following commands:

```bash
python src/main.py build
python src/main.py load
python src/main.py print nonsense
python src/main.py find good friends
```

## Testing instructions

Run the test suite with:

```bash
pytest
```

## Dependencies

- `requests`
- `beautifulsoup4`
- `pytest`
- `pytest-cov`
