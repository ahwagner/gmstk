__author__ = 'Alex H Wagner'

import paramiko
import time
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
        self._terminal = None
        self._cmd_prompt = PROMPT
        self._sep = '===ENDLINUS==='

    def connect(self):
        self._client.connect(self._name, username=self._user, port=self._port)
        self._sftp_client = self._client.open_sftp()
        self._terminal = self._client.invoke_shell()
        try:
            r = self.recv_all(timeout=5, contains=self._cmd_prompt, count=1)
            print(r.stdout)
            self._cmd_prompt = r.stdout.strip()[-1]
        except TimeoutError as e:
            s = str(e)
            if s:
                a = s.strip().split(self._cmd_prompt)
                if len(a) > 1 and a[-1]:
                    c = a[-1]
                else:
                    c = s.strip()[-1]
                m = "\nCommand prompt doesn't contain '{0}'.\nConsider changing PROMPT to '{1}' in config.py." \
                    "\nConnection successful.".format(self._cmd_prompt, c)
                warnings.warn(m)
                self._cmd_prompt = c
            else:
                raise TimeoutError('No response from virtual terminal. Check connection.')

    def command(self, command, timeout=5, verbose=False):
        """Returns list of stdout lines and list of stderr lines"""
        if verbose:
            print('Executing remote command:', command)
        self._terminal.send(command + '; \\\necho {0}\n'.format(self._sep))
        r = self.recv_all(contains=self._sep, timeout=timeout)
        s = r.stdout
        try:
            p, s, c = s.split(self._sep)
        except ValueError:
            raise ValueError('s is {0}'.format(s))
        if not c.endswith(self._sep):
            r = self.recv_all(contains=self._cmd_prompt, timeout=timeout, count=1)
        r.stdout = s.strip().splitlines()
        r.stderr = r.stderr.strip().splitlines()
        return r

    def recv_all(self, timeout=0, contains=None, count=2):
        t = 0
        interval = 0.1
        first = True
        e = r = ''
        while first or (contains and r.count(contains) < count):
            while not self._terminal.recv_ready() or self._terminal.recv_stderr_ready():
                time.sleep(interval)
                t += interval
                if timeout and t > timeout:
                    raise TimeoutError(r)
            first = False
            while self._terminal.recv_ready():
                r += self._terminal.recv(1000).decode('utf-8', 'ignore')
            while self._terminal.recv_stderr_ready():
                e += self._terminal.recv_stderr(1000).decode('utf-8', 'ignore')
        return Bunch(stdout=r, stderr=e)

    def open(self, filename, update_cwd=True):
        if update_cwd:
            r = self.pwd()
            pwd = r.stdout[0]
            self._sftp_client.chdir(pwd)
        remote_file = self._sftp_client.open(filename)
        return remote_file

    def ftp_get(self, remote, local=None, update_cwd=True, recursive=False):
        if local is None:
            p = Path(remote)
            local = p.name
        local = local.rstrip('/')
        remote = remote.rstrip('/')
        if update_cwd:
            r = self.pwd()
            pwd = r.stdout[0]
            self._sftp_client.chdir(pwd)
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
            r = self.pwd()
            pwd = r.stdout[0]
            self._sftp_client.chdir(pwd)
        if recursive:
            # Check if local is a directory
            if not os.stat(local).st_mode // 2**15:
                # make remote directory
                # self._sftp_client.mkdir(remote) # This doesn't appear to work correctly.
                cwd = self._sftp_client.getcwd()
                if cwd is None:
                    cwd = self.echo('$HOME')
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

    def ls(self, *args, **kwargs):
        r = self.command(' '.join(['ls', '-1'] + [str(x) for x in args]), **kwargs)
        r.stdout = [x.rstrip('/') for x in r.stdout if x not in ['./', '../']]
        return r

    def __getattr__(self, item):
        return lambda *args, **kwargs: self.command(' '.join([item] + [str(x) for x in args]), **kwargs)

    def disconnect(self):
        self._sftp_client.close()
        self._client.close()
