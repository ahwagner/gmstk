from gmstk.linusbox import *
import os
import shutil


def enquote(string):
    return "'" + string + "'"


class TestLinusBox:

    test_dir = 'oh no'

    @classmethod
    def setup_class(cls):
        cls.linus = LinusBox()
        cls.linus.connect()
        cls.cwd = os.getcwd()

    @classmethod
    def teardown_class(cls):
        cls.linus.cd()
        cls.linus.rm('-rf', enquote(cls.test_dir))
        cls.linus.disconnect()
        x = os.getcwd()
        os.chdir(cls.cwd)
        os.remove('test2.txt')
        shutil.rmtree('test_dir')

    def a_mkdir_test(self):
        # make a test dir
        self.linus.mkdir(enquote(self.test_dir))
        r = self.linus.ls()
        assert self.test_dir in r.stdout, 'r is {0}'.format(r.stdout)

    def b_cd_test(self):
        # cd to test dir
        self.linus.cd(enquote(self.test_dir))
        r = self.linus.ls()
        assert not r.stdout, 'r is {0}'.format(r.stdout)

    def c_touch_test(self):
        # make a test file
        self.linus.touch('test.txt')
        r = self.linus.ls()
        assert 'test.txt' in r.stdout, 'r is {0}'.format(r.stdout)

    def d_ftp_get_test(self):
        # copy the test file to local
        self.linus.ftp_get('test.txt', 'test2.txt')
        assert os.path.isfile('test2.txt')

    def e_ftp_put_test(self):
        #
        self.linus.ftp_put('test2.txt')
        r = self.linus.ls()
        assert 'test2.txt' in r.stdout, 'r is {0}'.format(r.stdout)

    def f_ftp_recursive_get_test(self):
        # copy a directory to local
        self.linus.cd()
        self.linus.ftp_get(self.test_dir, 'test_dir', recursive=True)
        r = os.listdir()
        assert 'test_dir' in r, 'r is {0}'.format(r)
        assert os.listdir('test_dir') == ['test.txt', 'test2.txt']

    def g_ftp_recursive_put_test(self):
        # copy a local directory to remote
        self.linus.ftp_put('test_dir', recursive=True)
        r = self.linus.ls()
        assert 'test_dir' in r.stdout, 'r is {0}'.format(r.stdout)
        r = self.linus.ls('test_dir').stdout
        assert r == ['test.txt', 'test2.txt'], 'r is {0}'.format(r)
