# sortxml - a simple XML element sorter

This module can be used by importing `sortxml.sort_xml` or by running standalone from the command-line.

## Using `sort_xml()`:

Returns an ElementTree representing the resulting whole document. ElementTree can easily be converted to string or written to a file like so:
    
```python
    >>> foo_str = ET.tostring(sort_xml(xml_doc, node_path, sort_attr).getroot())
        # Or...
    >>> sort_xml(xml_doc, node_path, sort_attr).write('foo.xml')
```

### Required arguments:
* `xml_doc` -- a text IO stream (such as an open file object), Path object pointing to an XML
  file, string representing the file path, or string containing the file contents of a valid XML file. Can't take
  an ElementTree instance because we need to use our own parser to keep track of namespaces.
* `node_path` -- a string containing the path to the node you want to sort the children of in the XPath language
  of the etree module
* `sort_attr` -- the attribute of the child elements to use as the sort key

### Optional arguments:
* `use_text` -- use `sort_attr` as the name of a subelement of the path's children whose text will be the
  sort key (default: False)
* `sort_as_datetime` -- try to parse the values of the sort key as a datetime using the `dateutil` module and sort
  chronologically (default: False, mutually exclusive with `sort_as_decimal`)
* `sort_as_decimal` -- try to parse the values of the sort key as a decimal and sort numerically (useful to keep
  '10' from showing up right after '1') (default: False, mutually exclusive with `sort_as_datetime`)
* `descending` -- sort in descending order instead of ascending (default: False)

## Usage on the command line:

Run `python -m sortxml -h` to display this help text.

Usage: sortxml [-h] [-v] [-r] [-t] [--datetime | --decimal] [-o OUTPUT_FILE] input_file sort_xpath sort_attr

A simple XML element sorter.  Will sort the children of selected elements using a given attribute's value or subelement's text as the sort key.  
Example usage:

        $ python sortxml.py ARForm_orig.rdl "./DataSets/DataSet[@Name='ARForm']/Fields" Name -o ARForm.rdl

### Positional arguments:
* _**input_file**_ – File path to the source xml file.
* _**sort_xpath**_ – XPath-style selector for elements to sort the children of. This has the same limitations as Python's ElementTree module.
* _**sort_attr**_ – The name of the attribute to use as the sort key.

### Options:
* _**-h, --help**_ – show this help message and exit
* _**-v, --version**_ – show program's version number and exit
* _**-r, --reverse, --descending**_ – Sort the child elements in reverse (descending) order.
* _**-t, --text, --use-text**_ – Treat the sort attribute name as the name of a subelement whose text is the sort key.
* _**--datetime, --as-datetime**_ – Try to parse the sort key as a date/time value. Mutually exclusive with --decimal.
* _**--decimal, --as-decimal**_ – Try to parse the sort key as a decimal number. Mutually exclusive with --datetime.
* _**-o OUTPUT_FILE, --output OUTPUT_FILE**_ – File path to the destination file. (Default is to append '_sorted' to the filename before the extension.)

    