from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
import sys

env = Environment(loader=FileSystemLoader('templates'))
try:
    env.get_template('index.html')
    print('TEMPLATE_OK')
except TemplateSyntaxError as e:
    print('TEMPLATE_ERR', e)
    sys.exit(1)
except Exception as e:
    print('OTHER_ERR', e)
    sys.exit(2)
