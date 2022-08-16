#!/usr/bin/python310

"""Simple XML element sorter.

This module can be used by importing `sort_xml` or by running standalone from the command-line.

"""

#  Copyright (c) 2022, Chris Koch <kopachris@gmail.com>
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#      (1) Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#      (2) Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#
#      (3)The name of the author may not be used to
#      endorse or promote products derived from this software without
#      specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
#  INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
#  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
#  STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
#  IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.

__version__ = (0, 1, 0)
__version_str__ = '.'.join([str(v) for v in __version__])

__description__ = """
    A simple XML element sorter.  Will sort the children of selected elements
    using a given attribute's value or subelement's text as the sort key.
    Example usage:
        $ python sortxml.py ARForm_orig.rdl "./DataSets/DataSet[@Name='ARForm']/Fields" Name -o ARForm.rdl
"""

import argparse as ap
import xml.etree.ElementTree as ET
from pathlib import Path
from io import TextIOWrapper
from codecs import BOM_UTF8
from decimal import Decimal
from dateutil.parser import parse as parse_dt


class NSElement(ET.Element):
    """Subclass of ElementTree.Element which keeps track of its TreeBuilder and namespaces if available."""
    
    def __init__(self, *args, **kwargs):
        self._ns_map = dict()
        self._builder = None
        if 'builder' in kwargs:
            builder = kwargs.pop('builder')
            self._builder = builder
            if hasattr(builder, 'ns_map'):
                self._ns_map = builder.ns_map
        super().__init__(*args, **kwargs)
        
    def find(self, path, namespaces=None):
        if namespaces is None:
            namespaces = self._ns_map
        return super().find(path, namespaces)

    def findall(self, path, namespaces=None):
        if namespaces is None:
            namespaces = self._ns_map
        return super().findall(path, namespaces)
        
    def findtext(self, path, default=None, namespaces=None):
        if namespaces is None:
            namespaces = self._ns_map
        return super().findtext(path, default, namespaces)
        
    def iterfind(self, path, namespaces=None):
        if namespaces is None:
            namespaces = self._ns_map
        return super().iterfind(path, namespaces)


class NSTreeBuilder(ET.TreeBuilder):
    """Subclass of ElementTree.TreeBuilder which adds namespaces in the document to the namespace registry."""
    
    def __init__(self, **kwargs):
        self.ns_map = dict()
        if 'element_factory' in kwargs:
            del kwargs['element_factory']
        super().__init__(element_factory=NSElement, **kwargs)
    
    def start_ns(self, prefix, uri):
        self.ns_map[prefix] = uri
        ET.register_namespace(prefix, uri)
        
    def start(self, tag, attrs):
        if self._factory is NSElement:
            self._flush()
            self._last = e = self._factory(tag, attrs, builder=self)
            if self._elem:
                self._elem[-1].append(e)
            elif self._root is None:
                self._root = e
            self._elem.append(e)
            self._tail = 0
            return e
        else:
            return super().start(tag, attrs)
        
    def _handle_single(self, factory, insert, *args):
        if factory is NSElement:
            e = factory(*args, builder=self)
            if insert:
                self._flush()
                self._last = e
                if self._elem:
                    self._elem[-1].append(e)
                self._tail = 1
            return e
        else:
            return super()._handle_single(factory, insert, *args)


def sort_xml(xml_doc, node_path, sort_attr, use_text=False, sort_as_datetime=False, sort_as_decimal=False,
             descending=False):
    """Sort the children of a selection of elements in an XML document. Returns an ElementTree representing the
    resulting whole document. ElementTree can easily be converted to string or written to a file like so:
    
    >>> foo_str = ET.tostring(sort_xml(xml_doc, node_path, sort_attr).getroot())
    >>> sort_xml(xml_doc, node_path, sort_attr).write('foo.xml')

    Required arguments:
    -------------------
    * `xml_doc` -- a text IO stream (such as an open file object), Path object pointing to an XML
      file, string representing the file path, or string containing the file contents of a valid XML file. Can't take
      an ElementTree instance because we need to use our own parser to keep track of namespaces.
    * `node_path` -- a string containing the path to the node you want to sort the children of in the XPath language
      of the etree module
    * `sort_attr` -- the attribute of the child elements to use as the sort key

    Optional arguments:
    -------------------
    * `use_text` -- use `sort_attr` as the name of a subelement of the path's children whose text will be the
      sort key (default: False)
    * `sort_as_datetime` -- try to parse the values of the sort key as a datetime using the `dateutil` module and sort
      chronologically (default: False, mutually exclusive with `sort_as_decimal`)
    * `sort_as_decimal` -- try to parse the values of the sort key as a decimal and sort numerically (useful to keep
      '10' from showing up right after '1') (default: False, mutually exclusive with `sort_as_datetime`)
    * `descending` -- sort in descending order instead of ascending (default: False)
    
    """
    # check parameters

    # xml_doc
    if isinstance(xml_doc, TextIOWrapper) and xml_doc.readable():
        # xml_doc is a readable text stream, let's read it
        # but first make sure to remove any byte order marker

        if xml_doc.encoding != 'utf-8-sig':
            xml_doc.reconfigure(encoding='utf-8-sig')

        xml_str = xml_doc.read()
    elif isinstance(xml_doc, Path) and xml_doc.is_file():
        # xml_doc is a Path object to a file
        xml_str = xml_doc.read_text('utf-8-sig')  # utf-8-sig to remove byte order marker
    elif isinstance(xml_doc, str) and Path(xml_doc).is_file():
        # xml_doc is a filename
        xml_str = Path(xml_doc).read_text('utf-8-sig')
    elif isinstance(xml_doc, str) and len(xml_doc) > 0:
        # xml_doc hopefully contains valid XML
        if xml_doc.startswith(BOM_UTF8.decode('utf-8')):
            xml_str = xml_doc[3:]
        else:
            xml_str = xml_doc
    else:
        raise TypeError("sort_xml() requires first parameter must be a string, readable IO stream, or path for a "
                        f"valid xml file! xml_doc: {repr(xml_doc)}")
    
    # sort_attr
    if not (isinstance(sort_attr, str) and len(sort_attr) > 0):
        raise TypeError("sort_xml() requires sort attribute must be a non-empty string!\n\t"
                        f"sort_attr: {repr(sort_attr)}")
    else:
        sort_attr = sort_attr.strip()
    if not (sort_attr.replace('_', '').isalnum() and (sort_attr[0].isalpha() or sort_attr[0] == '_')):
        raise ValueError("Sort attribute passed to sort_xml() is an invalid name!\n\t"
                         f"sort_attr: {repr(sort_attr)}")
    
    # make our element tree using our custom treebuilder and get all the parents we have to sort children of

    dom = ET.fromstring(xml_str, ET.XMLParser(target=NSTreeBuilder()))
    matching_parents = dom.findall(node_path)
    
    # check what kind of sorting we're doing and do it
    # TODO might be faster if we do the check once and then run the appropriate for loop?
    for par in matching_parents:
        if use_text:
            if sort_as_datetime:
                par[:] = sorted(par, key=lambda x: parse_dt(x.findtext(sort_attr)), reverse=descending)
            elif sort_as_decimal:
                par[:] = sorted(par, key=lambda x: Decimal(x.findtext(sort_attr)), reverse=descending)
            else:
                par[:] = sorted(par, key=lambda x: x.findtext(sort_attr), reverse=descending)
        elif sort_as_datetime:
            par[:] = sorted(par, key=lambda x: parse_dt(x.get(sort_attr)), reverse=descending)
        elif sort_as_decimal:
            par[:] = sorted(par, key=lambda x: Decimal(x.get(sort_attr)), reverse=descending)
        else:
            par[:] = sorted(par, key=lambda x: x.get(sort_attr), reverse=descending)
            
    return ET.ElementTree(dom)


if __name__ == '__main__':
    argp = ap.ArgumentParser(description=__description__, formatter_class=ap.RawDescriptionHelpFormatter)
    argp.add_argument('-v', '--version', action='version', version=f"%(prog)s -- version {__version_str__}")
    argp.add_argument('input_file', type=Path, help="File path to the source xml file.")
    argp.add_argument('sort_xpath',
                      help="XPath-style selector for elements to sort the children of.  This has the same limitations "
                      "as Python's ElementTree module.")
    argp.add_argument('sort_attr', help="The name of the attribute to use as the sort key.")
    argp.add_argument('-r', '--reverse', '--descending', action='store_true', dest='descending',
                      help="Sort the child elements in reverse (descending) order.")
    argp.add_argument('-t', '--text', '--use-text', action='store_true', dest='use_text',
                      help="Treat the sort attribute name as the name of a subelement whose text is the sort key.")
    sort_style = argp.add_mutually_exclusive_group()
    sort_style.add_argument('--datetime', '--as-datetime', action='store_true', dest='as_datetime',
                            help="Try to parse the sort key as a date/time value.  Mutually exclusive with --decimal.")
    sort_style.add_argument('--decimal', '--as-decimal', action='store_true', dest='as_decimal',
                            help="Try to parse the sort key as a decimal number.  Mutually exclusive with --datetime.")
    argp.add_argument('-o', '--output', type=Path, dest='output_file',
                      help="File path to the destination file.  (Default is to append '_sorted' to the filename.)")
    
    argv = argp.parse_args()
    
    xml_doc = argv.input_file
    sort_path = argv.sort_xpath
    sort_attr = argv.sort_attr
    sort_desc = argv.descending
    use_text = argv.use_text
    as_dt = argv.as_datetime
    as_dec = argv.as_decimal
    
    sorted_xml = sort_xml(xml_doc, sort_path, sort_attr, use_text, as_dt, as_dec, sort_desc)
    
    if not hasattr(argv, 'output_file'):
        new_filename = xml_doc.stem + '_sorted'
        out_file = xml_doc.with_stem(new_filename)
    else:
        out_file = argv.output_file
    
    out_file.write_text(ET.tostring(sorted_xml.getroot(), encoding='unicode'), encoding='utf-8')
        
    print(f"Output sorted file as `{out_file}`")
