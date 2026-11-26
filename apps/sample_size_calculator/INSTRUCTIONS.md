# Project Instructions

This file explains how to work with the Python virtual environment and how to start or stop the Dash application from the terminal.

## Open the project folder

In Terminal:

```bash
cd /Users/sainathdaakuri/Documents/sample_size_calculator_ab_test
```

## Start the virtual environment

If the virtual environment already exists, activate it with:

```bash
source .venv/bin/activate
```

After activation, your terminal usually shows `(.venv)` at the beginning of the prompt.

You can confirm the active Python version with:

```bash
python3 --version
which python3
```

## Deactivate the virtual environment

When you are done, leave the virtual environment with:

```bash
deactivate
```

This returns your terminal to the normal system shell environment.

## Start the Dash app

Make sure you are inside the project folder and the virtual environment is active, then run:

```bash
python3 app.py
```

Dash will start a local development server. Open the URL shown in the terminal, usually:

- [http://127.0.0.1:8050](http://127.0.0.1:8050)

## Stop the Dash app

If the Dash app is running in the terminal, stop it by pressing:

```text
Ctrl + C
```

This ends the local server and returns control to the terminal.

## Typical daily workflow

```bash
cd /Users/sainathdaakuri/Documents/sample_size_calculator_ab_test
source .venv/bin/activate
python3 app.py
```

When finished:

1. Press `Ctrl + C` to stop the app
2. Run:

```bash
deactivate
```

## If the app does not start

Check that:

- You are in the correct project folder
- The virtual environment is active
- Dependencies were installed with `pip install -r requirements.txt`

You can verify package installation with:

```bash
pip list
```
