import paramiko
import warnings
from pathlib import Path
from gmstk.config import *


KNOWN_HOSTS = HOME + "/.ssh/known_hosts"
# Consider rewriting this with the fabric module once it is compatible with 3.x


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class LinusBox:

    def __init__(self, name=LINUSNAME, user=USER, port=22):
        self._name = name
        self._user = user
        self._port = port
        self._client = paramiko.SSHClient()
        self._client.get_host_keys().load(KNOWN_HOSTS)
        self._sftp_client = None
        self._cwd = ''

    def connect(self):
        self._client.connect(self._name, username=self._user, port=self._port)
        self._cwd = self.command('pwd').stdout[0]
        self._sftp_client = self._client.open_sftp()

    def command(self, command, timeout=5, **kwargs):
        """Returns list of stdout lines and list of stderr lines"""
        if 'verbose' in kwargs:
            warnings.warn("Use of 'verbose' in command is deprecated.", DeprecationWarning)
        if command == 'pwd':
            command = 'echo "$HOME"'
        if command.startswith('cd'):
            submit_command = command
        else:
            submit_command = 'cd {0}; '.format(self._cwd) + command
        response = self._client.exec_command(submit_command, timeout=timeout)
        out = [x.strip() for x in response[1].readlines()]
        err = [x.strip() for x in response[2].readlines()]
        r = Bunch(
            stdout=out,
            stderr=err
        )
        return r

    def open(self, filename, update_cwd=True):
        if update_cwd:
            self._sftp_client.chdir(self._cwd.strip('"\''))
        remote_file = self._sftp_client.open(filename)
        return remote_file

    def cd(self, directory=''):
        directory = directory.strip('\'"')
        if directory == '':
            full_dir = ''
        elif directory.startswith('/'):
            full_dir = directory
        else:
            full_dir = '/'.join([self._cwd, directory])
        if ' ' in full_dir:
            full_dir = "'{0}'".format(full_dir)
        resp = self.command('cd {0}'.format(full_dir))
        if not resp.stderr:
            server_dir = self.command('cd {0}; echo $PWD'.format(full_dir)).stdout[0]
            if ' ' in server_dir:
                server_dir = '"{0}"'.format(server_dir)
            self._cwd = server_dir
        return resp

    def pwd(self):
        return self._cwd

    def ftp_get(self, remote, local=None, update_cwd=True, recursive=False):
        if local is None:
            p = Path(remote)
            local = p.name
        local = local.rstrip('/')
        remote = remote.rstrip('/')
        if update_cwd:
            self._sftp_client.chdir(self._cwd.strip("'\""))
        if recursive:
            # Check if remote is a directory
            if not self._sftp_client.stat(remote).st_mode // 2**15:
                # make local directory
                try:
                    os.mkdir(local)
                except FileExistsError:
                    pass
                start = os.getcwd()
                os.chdir(local)
                # get contents of remote directory
                dir_list = self._sftp_client.listdir(remote)
                # call ftp_get on each file/directory found (exclude ./ and ../)
                for d in dir_list:
                    self.ftp_get('/'.join([remote, d]), d, update_cwd=False)
                os.chdir(start)
                return
        self._sftp_client.get(remote, local)

    def ftp_put(self, local, remote=None, update_cwd=True, recursive=False):
        if remote is None:
            p = Path(local)
            remote = p.name
        local = local.rstrip('/')
        remote = remote.rstrip('/')
        if update_cwd:
            self._sftp_client.chdir(self._cwd.strip("'\""))
        if recursive:
            # Check if local is a directory
            if not os.stat(local).st_mode // 2**15:
                # make remote directory
                # self._sftp_client.mkdir(remote) # This doesn't appear to work correctly.
                cwd = self._sftp_client.getcwd()
                if cwd is None:
                    cwd = self.pwd() # This takes advantage of the fact that the channel always resets
                self.mkdir('/'.join([cwd, remote]))
                self._sftp_client.chdir(remote)
                # get contents of local directory
                dir_list = os.listdir(local)
                # call ftp_put on each file/directory found (exclude ./ and ../)
                for d in dir_list:
                    self.ftp_put('/'.join([local, d]), d, update_cwd=False)
                self._sftp_client.chdir(cwd)
                return
        self._sftp_client.put(local, remote)

    def __getattr__(self, item):
        return lambda *args, **kwargs: self.command(' '.join([item] + [str(x) for x in args]), **kwargs)

    def disconnect(self):
        self._sftp_client.close()
        self._client.close()