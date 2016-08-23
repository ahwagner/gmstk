from gmstk.linusbox import *
from collections import defaultdict
import xml.etree.ElementTree as ET
import logging


class GMSModel:

    linus = LinusBox()
    linus.connect()

    gms_type = 'model'

    def __init__(self, model_id, **kwargs):
        self.model_id = model_id
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])
        self.filter_values = {'id': self.model_id}

    def update(self, raw=False):
        """raw=False processes attributes extracted from call response. raw=True returns the call response instead."""
        logging.debug('Update requested: %s', self.model_id)
        vd = self.show_values
        keys = sorted(vd)
        v_call = ','.join([vd[x] for x in keys])
        fd = self.filter_values
        f_keys = sorted(fd)
        f_call = ','.join(['{0}={1}'.format(x, fd[x]) for x in f_keys])
        c = 'genome {0} list --noheaders --style=xml'.format(self.gms_type)
        if f_call:
            c += ' --filter {0}'.format(f_call)
        if v_call:
            c += ' --show {0}'.format(v_call)
        r = self.linus.command(c, timeout=15, style='file')
        if raw:
            return r
        # From here, it is expected that there is only one result object
        tree = ET.parse(r.stdout)
        object = tree.getroot().find('object')
        d = dict()
        for key in keys:
            value = object.find(self.show_values[key]).text
            d[key] = value
        self._set_attr_from_dict(d)

    def _set_attr_from_dict(self, d):
        for k in d:
            if d[k] == '<NULL>':
                continue
            setattr(self, k, d[k])

    @classmethod
    def search(cls, search_terms):
        f_call = ','.join(['{0}={1}'.format(k, v) for k, v in search_terms.items()])
        c = 'genome {0} list --style=xml --noheader --filter {1} --show id'.format(cls.gms_type, f_call)
        r = cls.linus.command(c, timeout=15)
        return r.stdout

    def attributes(self):
        return {x: getattr(self, x) for x in dir(self) if x not in dir(self.__class__)}

    def copy(self):
        """returns a shallow copy of the model"""
        c = self.__class__(self.model_id, update_on_init=False)
        attr = self.attributes()
        c._set_attr_from_dict(attr)
        return c


class GMSModelGroup(GMSModel):

    def __init__(self, *args, **kwargs):
        GMSModel.__init__(self, *args, **kwargs)
        self.models = {}

    def __len__(self):
        return len(self.models)

    @property
    def model_labels(self):
        return set(self.models.keys())

    def copy(self):
        c = self.__class__(self.model_id, update_models_on_init=False)
        for model_id, model in self.models.items():
            c.models[model_id] = model.copy()
        return c

    def split_models_on_field(self, field, model_ids_only=False):
        d = defaultdict(list)
        for model in self.models.values():
            d[getattr(model, field)].append(model)
        if model_ids_only:
            for key in d:
                d[key] = sorted([x.model_id for x in d[key]])
        return dict(d)

    def update(self, raw=False, update_models=True):
        base = self.__class__.__bases__[1]
        r = GMSModel.update(self, raw=True)
        keys = sorted(self.show_values)
        tree = ET.parse(r.stdout)
        for object in tree.getroot().findall('object'):
            d = dict()
            model_id = object.attrib['id']
            model = base(model_id, update_on_init=False)
            for key in keys:
                value = object.find(self.show_values[key]).text
                d[key] = value
            model._set_attr_from_dict(d)
            self.models[model_id] = model
