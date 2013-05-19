"""
This is a monkey patch function because the RN-XV wifly doesn't send the
right type of header as a valid HTTP request. Most servers figure this
out but cherrypy is a little particular about the spec.

As such we changet the line:

        self.simple_response("400 Bad Request", "HTTP requires CRLF terminators")

to accept \n\n as well

"""
from cherrypy.wsgiserver.wsgiserver2 import LF, CRLF, TAB, SPACE, COLON, SEMICOLON, EMPTY, NUMBER_SIGN, ASTERISK, FORWARD_SLASH, QUESTION_MARK, quoted_slash 
from cherrypy.wsgiserver.wsgiserver2 import comma_separated_headers, unquote

def read_request_line(self):
    # HTTP/1.1 connections are persistent by default. If a client
    # requests a page, then idles (leaves the connection open),
    # then rfile.readline() will raise socket.error("timed out").
    # Note that it does this based on the value given to settimeout(),
    # and doesn't need the client to request or acknowledge the close
    # (although your TCP stack might suffer for it: cf Apache's history
    # with FIN_WAIT_2).
    request_line = self.rfile.readline()

    # Set started_request to True so communicate() knows to send 408
    # from here on out.
    self.started_request = True
    if not request_line:
        return False

    if request_line == CRLF:
        # RFC 2616 sec 4.1: "...if the server is reading the protocol
        # stream at the beginning of a message and receives a CRLF
        # first, it should ignore the CRLF."
        # But only ignore one leading line! else we enable a DoS.
        request_line = self.rfile.readline()
        if not request_line:
            return False

    # this is the mod by AF to deal with the RN-XV request issue
    if not request_line.endswith(CRLF):
        if request_line.endswith(LF):
            # we probably have a valid request from an RN-XV
            request_line = request_line[:-1] + CRLF
        else:
            self.simple_response("400 Bad Request", "HTTP requires CRLF terminators ANDREW")
            return False

    try:
        method, uri, req_protocol = request_line.strip().split(SPACE, 2)
        rp = int(req_protocol[5]), int(req_protocol[7])
    except (ValueError, IndexError):
        self.simple_response("400 Bad Request", "Malformed Request-Line")
        return False

    self.uri = uri
    self.method = method

    # uri may be an abs_path (including "http://host.domain.tld");
    scheme, authority, path = self.parse_request_uri(uri)
    if NUMBER_SIGN in path:
        self.simple_response("400 Bad Request",
                             "Illegal #fragment in Request-URI.")
        return False

    if scheme:
        self.scheme = scheme

    qs = EMPTY
    if QUESTION_MARK in path:
        path, qs = path.split(QUESTION_MARK, 1)

    # Unquote the path+params (e.g. "/this%20path" -> "/this path").
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
    #
    # But note that "...a URI must be separated into its components
    # before the escaped characters within those components can be
    # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
    # Therefore, "/this%2Fpath" becomes "/this%2Fpath", not "/this/path".
    try:
        atoms = [unquote(x) for x in quoted_slash.split(path)]
    except ValueError:
        ex = sys.exc_info()[1]
        self.simple_response("400 Bad Request", ex.args[0])
        return False
    path = "%2F".join(atoms)
    self.path = path

    # Note that, like wsgiref and most other HTTP servers,
    # we "% HEX HEX"-unquote the path but not the query string.
    self.qs = qs

    # Compare request and server HTTP protocol versions, in case our
    # server does not support the requested protocol. Limit our output
    # to min(req, server). We want the following output:
    #     request    server     actual written   supported response
    #     protocol   protocol  response protocol    feature set
    # a     1.0        1.0           1.0                1.0
    # b     1.0        1.1           1.1                1.0
    # c     1.1        1.0           1.0                1.0
    # d     1.1        1.1           1.1                1.1
    # Notice that, in (b), the response will be "HTTP/1.1" even though
    # the client only understands 1.0. RFC 2616 10.5.6 says we should
    # only return 505 if the _major_ version is different.
    sp = int(self.server.protocol[5]), int(self.server.protocol[7])

    if sp[0] != rp[0]:
        self.simple_response("505 HTTP Version Not Supported")
        return False

    self.request_protocol = req_protocol
    self.response_protocol = "HTTP/%s.%s" % min(rp, sp)

    return True




def read_headers(rfile, hdict=None):
    """Read headers from the given stream into the given header dict.

    If hdict is None, a new header dict is created. Returns the populated
    header dict.

    Headers which are repeated are folded together using a comma if their
    specification so dictates.

    This function raises ValueError when the read bytes violate the HTTP spec.
    You should probably return "400 Bad Request" if this happens.
    """
    if hdict is None:
        hdict = {}

    while True:
        line = rfile.readline()
        if not line:
            # No more data--illegal end of headers
            raise ValueError("Illegal end of headers.")

        if not line.endswith(CRLF) and line.endswith(LF):
            line = line[:-1] + CRLF

        if line == CRLF:
            # Normal end of headers
            break
        if not line.endswith(CRLF):
            raise ValueError("HTTP requires CRLF terminators headers")

        if line[0] in (SPACE, TAB):
            # It's a continuation line.
            v = line.strip()
        else:
            try:
                k, v = line.split(COLON, 1)
            except ValueError:
                raise ValueError("Illegal header line.")
            # TODO: what about TE and WWW-Authenticate?
            k = k.strip().title()
            v = v.strip()
            hname = k

        if k in comma_separated_headers:
            existing = hdict.get(hname)
            if existing:
                v = ", ".join((existing, v))
        hdict[hname] = v

    return hdict
