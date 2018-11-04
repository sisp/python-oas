from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from six import iteritems

from .parsers import DEFAULT_PARSERS


class SchemaUnmarshaler(object):
    def __init__(self, spec, parsers=None):
        self.spec = spec
        if parsers is None:
            self.parsers = DEFAULT_PARSERS
        else:
            self.parsers = parsers

        self._unmarshalers = {
            'array': self._unmarshal_array,
            'object': self._unmarshal_object,
        }

    def unmarshal(self, value, schema):
        schema = self.spec.deref(schema)

        if 'allOf' in schema:
            # `value` should be a dict
            result = value.copy()  # shallow copy
            for sub_schema in schema['allOf']:
                # Each sub schema type should be a object,
                # and `unmarshaled` should be a dict.
                #
                # If multiple sub schemas define same property, latter wins.
                unmarshaled = self.unmarshal(value, sub_schema)
                result.update(unmarshaled)
            return result

        if 'type' not in schema:
            # oneOf and anyOf are unsupported
            return value

        try:
            handler = self._unmarshalers[schema['type']]
        except KeyError:
            handler = self._unmarshal_atom
        return handler(value, schema)

    def _unmarshal_array(self, value, schema):
        return [self.unmarshal(x, schema['items']) for x in value]

    def _unmarshal_object(self, value, schema):
        result = {}
        if 'properties' in schema:
            for k, sub_schema in iteritems(schema['properties']):
                if k in value:
                    sub_value = value[k]
                elif 'default' in sub_schema:
                    sub_value = sub_schema['default']
                else:
                    continue  # pragma: no cover
                result[k] = self.unmarshal(sub_value, sub_schema)
        return result

    def _unmarshal_atom(self, value, schema):
        try:
            parser = self.parsers[schema['format']]
        except KeyError:
            return value
        else:
            return parser(value)
