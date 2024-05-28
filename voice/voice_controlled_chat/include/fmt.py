# -*- coding: utf-8 -*-
from __future__ import print_function
import os, sys,time
from collections import namedtuple
from cli_helpers.tabular_output import TabularOutputFormatter
from cli_helpers.tabular_output.preprocessors import align_decimals, format_numbers
from pprint import pprint as pp
import sys, itertools
e=sys.exit
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

text_type = unicode if PY2 else str

def ppe(msg):
    pp(msg)
    e()
def fmt(data, header=['Col_1'], title=''):
    return get_formatted(title,data,header,join = True)
    
def pfmt(data, header=['Col_1'], title=''):
    print (fmt(data, header, title))
def pfmtdv(data, title='', vlen=80):
    counter = itertools.count(1)

    if len(data)>1:	
        print (fmt([[next(counter)]+[k,v[:vlen]] for k,v in data[0].items()],['Id','Key','Value'], title))
    elif len(data)==1:
        out=fmt([[k,v[:vlen]] for k,v in data[0].items()],['Key','Value'], title)
        #pp(out)
        #out=out.replace('\n', '\r\n')
        #pp(out)
        print(out)
    else:
        print (fmt([['No data']],[title], title))
def fmtd(data, title=''):
    counter = itertools.count(1)

    if len(data)>1:	
        print (fmt([[next(counter)]+ list(d.values()) for d in data],['id'] + list(data[0].keys()), title))
    elif len(data)==1:

        out=fmt([list(d.values()) for d in data],list(data[0].keys()), title)
        #pp(out)
        #out=out.replace('\n', '\r\n')
        #pp(out)
        return out
    else:
        return fmt([['No data']],[title], title)

def pfmtd(data, title=''):
    print(fmtd(data, title))
        
def fmtv(data, title='', cols=['Variable','Value']):
    return fmt([[k,v if type(v) in [bool] else str(v)[:120] ] for k,v in data.items()],cols, title)
    
def pfmtv(data, title='', cols=['Variable','Value']):
    print(fmtv(data, title, cols))


        
def psql(stmt, title='Query'):
    assert stmt
    max=0
    #for line in stmt.split(os.linesep):
    #    max= len(line) if len(line)>max else max
    pfmt([[stmt]], [title])
    
    
def unicode2utf8(arg):
    """
    Only in Python 2. Psycopg2 expects the args as bytes not unicode.
    In Python 3 the args are expected as unicode.
    """

    if PY2 and isinstance(arg, unicode):
        return arg.encode("utf-8")
    return arg


def utf8tounicode(arg):
    """
    Only in Python 2. Psycopg2 returns the error message as utf-8.
    In Python 3 the errors are returned as unicode.
    """

    if PY2 and isinstance(arg, str):
        return arg.decode("utf-8")
    return arg
    
def format_output( title, cur, headers, status, settings):
    output = []
    expanded = (settings.expanded or settings.table_format == 'vertical')
    table_format = ('vertical' if settings.expanded else
                    settings.table_format)
    max_width = settings.max_width
    case_function = settings.case_function
    formatter = TabularOutputFormatter(format_name=table_format)

    def format_array(val):
        if val is None:
            return settings.missingval
        if not isinstance(val, list):
            return val
        return '{' + ','.join(text_type(format_array(e)) for e in val) + '}'

    def format_arrays(data, headers, **_):
        data = list(data)
        for row in data:
            row[:] = [
                format_array(val) if isinstance(val, list) else val
                for val in row
            ]

        return data, headers

    output_kwargs = {
        'sep_title': 'RECORD {n}',
        'sep_character': '-',
        'sep_length': (1, 25),
        'missing_value': settings.missingval,
        'integer_format': settings.dcmlfmt,
        'float_format': settings.floatfmt,
        'preprocessors': (format_numbers, format_arrays),
        'disable_numparse': True,
        'preserve_whitespace': True
    }
    if not settings.floatfmt:
        output_kwargs['preprocessors'] = (align_decimals, )

    if title:
        output.append(title)

    if cur:
        headers = [case_function(utf8tounicode(x)) for x in headers]
        if max_width is not None:
            cur = list(cur)
        formatted = formatter.format_output(cur, headers, **output_kwargs)
        if isinstance(formatted, text_type):
            formatted = iter(formatted.splitlines())
        first_line = next(formatted)
        formatted = itertools.chain([first_line], formatted)

        if (not expanded and max_width and len(
                first_line) > max_width and headers):
            formatted = formatter.format_output(
                cur, headers, format_name='vertical', column_types=None, **output_kwargs)
            if isinstance(formatted, text_type):
                formatted = iter(formatted.splitlines())

        output = itertools.chain(output, formatted)

    if status:  # Only print the status if it's not None.
        output = itertools.chain(output, [status])

    return output
    
OutputSettings = namedtuple(
    "OutputSettings",
    "table_format dcmlfmt floatfmt missingval expanded max_width case_function style_output",
)
OutputSettings.__new__.__defaults__ = (
    None,
    None,
    None,
    "<null>",
    False,
    None,
    lambda x: x,
    None,
)

from pprint import pprint as pp
def get_formatted(title,data,headers,join = True):
    " Return string output for the sql to be run "
    expanded = False

    formatted = []
    settings = OutputSettings(table_format='psql', dcmlfmt='d', floatfmt='g',
                                   expanded=expanded)

    for title, rows, headers, status, sql, success, is_special in [[title, data, headers, None, None, None, False]]:
        formatted.extend(format_output(title, rows, headers, status, settings))
    if join:
        formatted = '\n'.join(formatted)

    return formatted

# Print iterations progress
def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()
    if iteration==total:
        print()

if __name__=="__main__":
    ptitle='Test title'
    plen=50
    num_years=9
    if 1:
        print_progress(0, num_years, prefix=ptitle, suffix='Complete', bar_length=plen)
        
        for i in range(10):
            #print(i)
            time.sleep(0.1)
            print_progress(i, num_years, prefix=ptitle, suffix='Complete', bar_length=plen)
    data=[]
    headers=['Col#%d' % i for i in range(10)]
    data.append([i for i in range(10)])
    print (get_formatted(ptitle,data,headers,join = True))