import pysftp

class SFTPClient:
    def __init__(self, host, port, username, private_key_path):
        self.cnopts = pysftp.CnOpts()
        self.cnopts.hostkeys = None
        self.host = host
        self.port = port
        self.username = username
        self.private_key_path = private_key_path
        self.sftp = None
        self.connect()
    
    def connect(self):
        """建立與SFTP伺服器的連線"""
        if not self.sftp:
            self.sftp = pysftp.Connection(
                self.host, 
                port=self.port, 
                username=self.username, 
                private_key=self.private_key_path, 
                cnopts=self.cnopts
            )
            print("已連線至SFTP伺服器!")
    
    def list_files(self, directory='.'):
        """列出指定目錄中的檔案"""
        self.connect()  # 確保連線是有效的
        files = self.sftp.listdir(directory)
        return files

    def change_directory(self, directory):
        """更改當前工作目錄"""
        self.connect()
        self.sftp.cwd(directory)
    
    def get_current_directory(self):
        """取得當前工作目錄"""
        self.connect()
        return self.sftp.pwd
    
    def upload_file(self, local_file, remote_file=None):
        """上傳檔案到SFTP伺服器"""
        self.connect()
        if remote_file is None:
            remote_file = f'/test/{local_file.split("/")[-1]}'
        self.sftp.put(local_file, remote_file)
        print(f"檔案 {local_file} 已上傳至 {remote_file}")
    
    def download_file(self, remote_file, local_file):
        """從SFTP伺服器下載檔案"""
        self.connect()
        self.sftp.get(remote_file, localpath=local_file)
        print(f"檔案 {remote_file} 已下載至 {local_file}")
    
    def create_directory(self, directory_name, mode=777):
        """在當前工作目錄中建立新目錄"""
        self.connect()
        self.sftp.mkdir(directory_name, mode=mode)
        print(f"目錄 {directory_name} 已建立")
    
    def quit(self):
        """關閉SFTP連線"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
            print("已斷開與SFTP伺服器的連線")
