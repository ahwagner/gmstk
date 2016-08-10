from gmstk.model import GMSModel, GMSModelGroup
import pandas as pd


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

    def get_gene_fpkm_value(self, ensembl_id=None, gene_symbol=None):
        if ensembl_id is not None:
            v = self.gene_fpkm_df.loc[self.gene_fpkm_df['tracking_id'] == ensembl_id, 'FPKM'].values[0]
        elif gene_symbol is not None:
            v = self.gene_fpkm_df.loc[self.gene_fpkm_df['gene_short_name'] == gene_symbol, 'FPKM'].values[0]
        return float(str(v))  # Automatically rounds and truncates

    def get_genes_fpkm_dict(self, ensembl_ids=None, gene_symbols=None):
        if ensembl_ids is not None:
            df = self.gene_fpkm_df.loc[self.gene_fpkm_df['tracking_id']\
                                           .isin(ensembl_ids), ['tracking_id', 'FPKM']]
            d = df.set_index('tracking_id')['FPKM'].to_dict()
        elif gene_symbols is not None:
            df = self.gene_fpkm_df.loc[self.gene_fpkm_df['gene_short_name']\
                                           .isin(gene_symbols), ['gene_short_name', 'FPKM']]
            d = df.set_index('gene_short_name')['FPKM'].to_dict()
        return d


class RNAModelGroup(RNAModel, GMSModelGroup):

    def __init__(self, model_id, update_models_on_init=True, *args, **kwargs):
        GMSModelGroup.__init__(self, model_id, *args, **kwargs)
        self.filter_values = {'model_groups.id': self.model_id}
        self.update(update_models=update_models_on_init)

    def update(self, raw=False, update_models=True):
        r = GMSModelGroup.update(self, raw=True)
        keys = sorted(self.show_values)
        for line in r.stdout:
            d = dict(zip(keys, line.split()))
            self.models[d['id']] = RNAModel(d['id'], False)
            self.models[d['id']].set_attr_from_dict(d)
