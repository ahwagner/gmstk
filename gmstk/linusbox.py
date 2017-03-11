import paramiko
import os
import shutil
import socket
import subprocess
from gmstk.config import *
from warnings import warn
from getpass import getpass

# Consider rewriting this with the fabric module once it is compatible with 3.x


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class LinusBox:

    def __init__(self, host=HOSTNAME, user=USERNAME, port=PORT):
        self._host = host or os.environ.get('GMSTK_SSH_HOST')
        self._user = user or os.environ.get('GMSTK_SSH_USER')
        self._port = port or os.environ.get('GMSTK_SSH_PORT')
        self._pass = None
        self._connected = False
        if not (self._host and self._user):
            print("Remote host credentials unspecified.".format(CONFIG_PATH))
            self.prompt_ssh_config()
        self._client = paramiko.SSHClient()
        try:
            self._client.get_host_keys().load(KNOWN_HOSTS)
        except FileNotFoundError:
            print("KNOWN_HOSTS file ({}) not found.".format(KNOWN_HOSTS))
        self._sftp_client = None
        self._cwd = ''
        if shutil.which('rsync'):
            self._use_rsync = True
        else:
            self._use_rsync = False

    def connect(self):
        kwargs = {}
        if self._pass is not None:
            kwargs['password'] = self._pass
        try:
            self._client.connect(self._host, username=self._user,
                                 port=self._port, timeout=3, **kwargs)
        except socket.timeout:
            warn("Connection timeout. Re-trying...")
            self._client.connect(self._host, username=self._user,
                                 port=self._port, timeout=10, **kwargs)
        except paramiko.ssh_exception.AuthenticationException:
            print('Authentication failed. Please specify password for {} on {}.'.format(self._user, self._host))
            self.prompt_ssh_pass()
            self.connect()
            return
        self._connected = True
        self._cwd = self.command('pwd').stdout[0]
        self._sftp_client = self._client.open_sftp()
        print('Successfully connected to remote host.')

    def prompt_ssh_config(self):
        self._host = input("Please enter the remote hostname: ")
        self._user = input("Please enter the remote username: ")
        save = input("Save to configuration file? (y/N): ")
        if save.lower().startswith('y'):
            self.save_config()

    def save_config(self):
        with open(CONFIG_PATH, 'w') as f:
            lines = ['from gmstk.defaults import *',
                     "HOSTNAME = '{}'".format(self._host),
                     "USERNAME = '{}'".format(self._user)]
            f.write("\n".join(lines))

    def prompt_ssh_pass(self):
        self._pass = getpass()

    def command(self, *args, **kwargs):
        if not self._connected:
            print("Not connected. Attempting connection now...")
            self.connect()
            print("Reattempting command...")
            return self.command(*args, **kwargs)
        try:
            return self._command(*args, **kwargs)
        except socket.timeout:
            print("Communication timeout. Reconnecting...")
            self.reconnect()
            print("Reattempting command...")
            return self.command(*args, **kwargs)

    def _command(self, command, timeout=5, style='list', **kwargs):
        """Returns list of stdout lines and list of stderr lines"""
        if command == 'pwd':
            command = 'echo "$HOME"'
        if command.startswith('cd'):
            submit_command = command
        else:
            submit_command = 'cd {0}; '.format(self._cwd) + command
        response = self._client.exec_command(submit_command, timeout=timeout)
        if style == 'list':
            out = [x.strip() for x in response[1].readlines()]
            err = [x.strip() for x in response[2].readlines()]
        elif style == 'file':
            out = response[1]
            err = response[2]
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
        if isinstance(local, Path):
            local = str(local)
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
        if os.path.dirname(local):
            os.makedirs(os.path.dirname(local), exist_ok=True)
        if self._use_rsync:
            self.rsync(remote, local)
        else:
            self._sftp_client.get(remote, local)

    def rsync(self, remote, local, mode='get'):
        args = ['rsync', '-P', '-e', 'ssh']
        if not remote.startswith('/'):
            remote = '/'.join([self._sftp_client.getcwd(), remote])
        if not local.startswith('/'):
            local = '/'.join([os.getcwd(), local])
        if self._pass:
            raise ValueError('Please set up SSH keys')
        if mode == 'get':
            args.append('{}@{}:"{}"'.format(self._user, self._host, remote))
            args.append(local)
        elif mode == 'put':
            args.append(local)
            args.append('{}@{}:"{}"'.format(self._user, self._host, remote))
        else:
            raise ValueError('Expected mode to be "get" or "put"')
        try:
            resp = subprocess.run(args, stderr=subprocess.PIPE)
            resp.check_returncode()
        except subprocess.CalledProcessError as e:
            if resp.returncode == 255:
                print('Connection failed. Retrying in 10s...')
                os.wait(10)
                self.rsync(remote, local, mode)
            else:
                raise e

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
        if self._use_rsync:
            self.rsync(remote, local, mode='put')
        else:
            self._sftp_client.put(local, remote)

    def __getattr__(self, item):
        return lambda *args, **kwargs: self.command(' '.join([item] + [str(x) for x in args]), **kwargs)

    def disconnect(self):
        self._sftp_client.close()
        self._client.close()
        self._connected = False

    def reconnect(self):
        self.disconnect()
        self.connect()
