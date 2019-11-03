import socket

def sendAudio(message, details = None, sound = 'alert'):
    if details is None:
        details = ''
    else:
        details = str(details).strip()
    try:
        server = "daq-expert.cms"
        port   = 50555
        body   = """<CommandSequence>
  <alarm sender='Trigger' sound='%s.wav' talk='%s'>%s</alarm>
</CommandSequence>
""" % (sound, message, details)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server, port))
        s.sendall(body)
        s.shutdown(socket.SHUT_WR)
        while s.recv(1024):
          pass
    except:
        print "Failed to send audio alarm to %s:%d:\n%s" % (server, port, body)


def audioAlert(message, details = None):
    try:
        sendAudio(message, details)
    except:
        pass

