from gmstk.rnaseq import RNAModel, RNAModelGroup
import pandas as pd


class TestRNASeq:

    @classmethod
    def setup_class(cls):
        test_models = [
            'e570f1bae29048348bf0f1d078ebf8e8',
            '83dbd7b005b644afb5c706eca2e51c0d',
            'e5b9068ce4cd4510ad3ed6d4df9391ab',
            'fbd22550ad954ebd950535f00ac39c0c',
            '340b04d8dbcc475691f850ac14d475a8',
            '4f8615c1e513445eaa16621c925ae0dd',
            '3adc43199fd54d2c80c1fb2bb37b05a0',
            '84b0d238d6b8410da864706096bfcc16',
            '9119663d738b4318b121a0bef08d98bc',
            '921e4502335947a5b0fb1040ad6fce60',
            '93887cf6bf984a53a3e15cf4d5ffef93',
            '97284e92abe6480e983901c6c276541a',
            '97bcb9f73f154c328007d6131e1102b6',
            'ba74c4c5ea6145d4af81e9e7f2808424',
            'd09a509181704a78a19689d821bdaede',
            'e500af4baa1943deaba23c17ac7762f4'
        ]
        cls.models = [RNAModel(x, update_on_init=False) for x in test_models]
        cls.models[0].update()
        cls.model_group = RNAModelGroup('34ec706e075d4335ab9bd83392e79d66', update_models_on_init=False)

    def a_rna_gene_expression_path_is_correct_test(self):
        model = self.models[0]
        assert model.gene_fpkm_path != ''
        assert model.gene_fpkm_path is not None

    def b_rna_expression_is_dataframe_test(self):
        model = self.models[0]
        assert model.gene_fpkm_df is not None
        assert isinstance(model.gene_fpkm_df, pd.DataFrame)
        assert not model.gene_fpkm_df.empty

    def c_models_in_model_group_test(self):
        ids = set([x.model_id for x in self.models])
        assert ids == self.model_group.model_ids

    def d_model_group_update_works_test(self):
        model = self.models[0]
        self.model_group.update()
        assert model.gene_fpkm_path == self.model_group.models[model.model_id].gene_fpkm_path