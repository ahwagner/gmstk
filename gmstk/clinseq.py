__author__ = 'Alex H Wagner'

from gmstk.model import GMSModel, GMSModelGroup

class ClinSeqModel(GMSModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gms_type = 'clin-seq'
        self.show_values = {'model_id': 'id',
                            'name': 'name',
                            'subject_common_name': 'subject.common_name',
                            'wgs_id': 'wgs_model.id',
                            'exome_id': 'exome_model.id',
                            'tumor_rnaseq': 'tumor_rnaseq_model.id',
                            'normal_rnaseq': 'normal_rnaseq_model.id'}
        self.filter_values = {'model_groups.id': self.model_id}


class ClinSeqModelGroup(ClinSeqModel, GMSModelGroup):
    pass

if __name__ == '__main__':
    from gmstk.rnaseq import RNAModel
    c = ClinSeqModelGroup('d7369c20395742568c79bdf0999d1f30')
    c.update()
    rnaseq = [RNAModel(x.tumor_rnaseq) for x in c.models if hasattr(x, 'tumor_rnaseq')]