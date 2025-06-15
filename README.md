Configurable Data Visualizer
============================

**Work in Progress**

This tool aims to automate the task of
- loading data from one or multiple files into a [DataFrame](https://pola.rs/),
- applying filtering and sorting,
- creating a [plot](https://plotly.com/) from it,
- assisting in data exploration (in a GUI pivot-style way), and
- allowing to repeat the exact same steps for any other set of files.

OK, but why not...
- ...just use a pivot table in a spreadsheet to do that? Because then you often have to repeat many manual steps when new data is to be added, or when a completely different set to files should be visualized. Also, Python offers so many more possibilities.
- ...just write a few lines of code to do exactly that with Python? Because then the data exploration part is very tedious and slow.


Requirements
------------

Just use the [pipfile](https://pipenv.pypa.io/) in `env/` with Python 3.13.


ToDo
----

- File input GUI.
