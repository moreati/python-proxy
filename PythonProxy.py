# -*- coding: cp1252 -*-
# <PythonProxy.py>
#
#Copyright (c) <2009> <F�bio Domingues - fnds3000 in gmail.com>
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""\
Copyright (c) <2009> <F�bio Domingues - fnds3000 in gmail.com> <MIT Licence>

                  **************************************
                 *** Python Proxy - A Fast HTTP proxy ***
                  **************************************

Neste momento este proxy � um Elie Proxy.

Suporta os m�todos HTTP:
 - OPTIONS;
 - GET;
 - HEAD;
 - POST;
 - PUT;
 - DELETE;
 - TRACE;
 - CONENCT.

Suporta:
 - Conex�es dos cliente em IPv4 ou IPv6;
 - Conex�es ao alvo em IPv4 e IPv6;
 - Conex�es todo o tipo de transmiss�o de dados TCP (CONNECT tunneling),
     p.e. liga��es SSL, como � o caso do HTTPS.

A fazer:
 - Verificar se o input vindo do cliente est� correcto;
   - Enviar os devidos HTTP erros se n�o, ou simplesmente quebrar a liga��o;
 - Criar um gestor de erros;
 - Criar ficheiro log de erros;
 - Colocar excep��es nos s�tios onde � previs�vel a ocorr�ncia de erros,
     p.e.sockets e ficheiros;
 - Rever tudo e melhorar a estrutura do programar e colocar nomes adequados nas
     vari�veis e m�todos;
 - Comentar o programa decentemente;
 - Doc Strings.

Funcionalidades futuras:
 - Adiconar a funcionalidade de proxy an�nimo e transparente;
 - Suportar FTP?.


(!) Aten��o o que se segue s� tem efeito em conex�es n�o CONNECT, para estas o
 proxy � sempre Elite.

Qual a diferen�a entre um proxy Elite, An�nimo e Transparente?
 - Um proxy elite � totalmente an�nimo, o servidor que o recebe n�o consegue ter
     conhecimento da exist�ncia do proxy e n�o recebe o endere�o IP do cliente;
 - Quando � usado um proxy an�nimo o servidor sabe que o cliente est� a usar um
     proxy mas n�o sabe o endere�o IP do cliente;
     � enviado o cabe�alho HTTP "Proxy-agent".
 - Um proxy transparente fornece ao servidor o IP do cliente e um informa��o que
     se est� a usar um proxy.
     S�o enviados os cabe�alhos HTTP "Proxy-agent" e "HTTP_X_FORWARDED_FOR".

"""

import select
import socket
import _thread

__version__ = '0.1.0 Draft 1'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'

REDIRECTIONS = {
    'localhost': '127.0.0.1',
}


class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        self.client = connection
        self.client_buffer = b''
        self.timeout = timeout
        self.method, self.path, self.protocol = self.get_base_header()
        if self.method=='CONNECT':
            self.method_CONNECT()
        elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            self.method_others()
        self.client.close()
        self.target.close()

    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find(b'\n')
            if end!=-1:
                break
        print(self.client_buffer[:end].decode('ascii')) # debug
        data = self.client_buffer[:end+1].decode('ascii').split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self):
        self._connect_target(self.path)
        self.client.send(f'{HTTPVER} 200 Connection established\n'
                         f'Proxy-agent: {VERSION}\n\n'
                         .encode('ascii'))
        self.client_buffer = b''
        self._read_write()        

    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]        
        path = self.path[i:]
        self._connect_target(host)
        self.target.send(f'{self.method} {path} {self.protocol}\n'
                         .encode('ascii'))
        self.target.send(self.client_buffer)
        self.client_buffer = b''
        self._read_write()

    def _connect_target(self, host):
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80

        # Override selected DNS lookups
        if host in REDIRECTIONS:
            soc_family = socket.AF_INET
            address = (REDIRECTIONS[host], port)
        else:
            addrinfo = socket.getaddrinfo(host, port)
            soc_family, _, _, _, address = addrinfo[0]

        self.target = socket.socket(soc_family)
        self.target.connect(address)

    def _read_write(self):
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break

def start_server(host='localhost', port=8080, IPv6=False, timeout=60,
                  handler=ConnectionHandler):
    if IPv6==True:
        soc_type=socket.AF_INET6
    else:
        soc_type=socket.AF_INET
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print(f"Serving on {host}:{port}.") # debug
    soc.listen(0)
    while 1:
        _thread.start_new_thread(handler, soc.accept()+(timeout,))

if __name__ == '__main__':
    start_server()
