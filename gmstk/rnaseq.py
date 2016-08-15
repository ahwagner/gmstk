from gmstk.model import GMSModel, GMSModelGroup
import pandas as pd
from collections import Counter
import warnings


class RNAModel(GMSModel):

    gms_type = 'model rna-seq'
    show_values = {'id': 'id',
                   'last_build_id': 'last_succeeded_build.id',
                   'last_build_path': 'last_succeeded_build.data_directory',
                   'subject_common_name': 'subject.common_name',
                   'individual_common_name': 'individual_common_name',
                   'extraction_label': 'subject.extraction_label',
                   'subject_name': 'subject_name'}

    def __init__(self, model_id, update_on_init=True, *args, **kwargs):
        super().__init__(model_id, *args, **kwargs)
        self.data = None
        self._gene_fpkm_df = None
        if update_on_init:
            self.update()

    @property
    def gene_fpkm_path(self):
        try:
            out = '/'.join((self.last_build_path, 'expression', 'genes.fpkm_tracking'))
        except AttributeError:
            out = None
        return out

    @property
    def gene_fpkm_df(self):
        if self._gene_fpkm_df is None:
            try:
                with RNAModel.linus.open(self.gene_fpkm_path, 'r') as f:
                    self._gene_fpkm_df = pd.read_csv(f, delimiter='\t')
            except TypeError:
                return None
        return self._gene_fpkm_df

    def get_gene_fpkm(self, ensembl_id=None, gene_symbol=None):
        if ensembl_id is not None:
            v = self.gene_fpkm_df.loc[self.gene_fpkm_df['tracking_id'] == ensembl_id, 'FPKM'].values[0]
        elif gene_symbol is not None:
            v = self.gene_fpkm_df.loc[self.gene_fpkm_df['gene_short_name'] == gene_symbol, 'FPKM'].values[0]
        return float(str(v))  # Automatically rounds and truncates

    def attributes(self):
        data = {
            x: getattr(self, x) for x in self.show_values
        }
        return pd.Series(data)

    def get_genes_fpkm(self, ensembl_ids=None, gene_symbols=None):
        if ensembl_ids is not None:
            df = self.gene_fpkm_df.loc[self.gene_fpkm_df['tracking_id']\
                                           .isin(ensembl_ids), ['tracking_id', 'FPKM']]
            d = df.set_index('tracking_id')['FPKM'].to_dict()
        elif gene_symbols is not None:
            df = self.gene_fpkm_df.loc[self.gene_fpkm_df['gene_short_name']\
                                           .isin(gene_symbols), ['gene_short_name', 'FPKM']]
            d = df.set_index('gene_short_name')['FPKM'].to_dict()
        return d


class RNAModelGroup(GMSModelGroup, RNAModel):

    def __init__(self, model_id, update_models_on_init=True, default_label='model_id', *args, **kwargs):
        GMSModelGroup.__init__(self, model_id, *args, **kwargs)
        self.filter_values = {'model_groups.id': self.model_id}
        self.update(update_models=update_models_on_init)
        self._default_label = default_label

    def get_gene_fpkm(self, ensembl_id=None, gene_symbol=None):
        d = dict()
        for model in self.models.values():
            d[getattr(model, self.default_label)] = model.get_gene_fpkm(ensembl_id=ensembl_id, gene_symbol=gene_symbol)
        return d

    def get_genes_fpkm(self, ensembl_ids=None, gene_symbols=None):
        df = self.gene_fpkm_df
        if ensembl_ids is not None:
            return df[df['tracking_id'].isin(ensembl_ids)]
        elif gene_symbols is not None:
            return df[df['gene_short_name'].isin(gene_symbols)]

    @property
    def default_label(self):
        return self._default_label

    @default_label.setter
    def default_label(self, value):
        counter = Counter()
        for model in self.models:
            counter[getattr(model, value)] += 1
        if counter.most_common(1)[0][1] > 1:
            warnings.warn('Label is not unique across models. Reverting to previous label ({0})'.format(self.default_label))
        else:
            self._default_label = value

    @property
    def gene_fpkm_df(self):
        colnames = ['gene_short_name', 'tracking_id']
        df = list(self.models.values())[0].gene_fpkm_df[colnames]
        for model in self.models.values():
            colnames.append(getattr(model, self.default_label))
            df = pd.concat([df, model.gene_fpkm_df['FPKM']], axis=1)
        df.columns = colnames
        return df

    def attributes(self):
        data = dict()
        for model_id, model in self.models.items():
            data[model_id] = model.attributes().to_dict()
        return pd.DataFrame.from_dict(data, orient='index')

    def get_differential_expression_models(self):
        pass


class DifferentialExpressionModel(GMSModel):

    gms_type = 'model differential-expression'
    show_values = {
        'id': 'id',
        'processing_profile': 'processing_profile.id',
        'condition_pairs': 'condition_pairs'
    }
