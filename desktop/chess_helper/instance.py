"""Focus an already running desktop app when it is opened again."""
import hashlib
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from .core import data_dir

def claim(app):
    name='BoardLens-'+hashlib.sha256(str(data_dir()).encode()).hexdigest()[:20]
    socket=QLocalSocket();socket.connectToServer(name)
    if socket.waitForConnected(200):socket.write(b'show');socket.waitForBytesWritten(500);socket.disconnectFromServer();return None
    QLocalServer.removeServer(name);server=QLocalServer(app);server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(name):raise RuntimeError('Could not open the BoardLens application channel.')
    return server

def attach(server,window):
    def accept():
        while server.hasPendingConnections():
            socket=server.nextPendingConnection();window.showNormal();window.raise_();window.activateWindow();socket.disconnectFromServer();socket.deleteLater()
    server.newConnection.connect(accept);accept();window._instance_server=server
