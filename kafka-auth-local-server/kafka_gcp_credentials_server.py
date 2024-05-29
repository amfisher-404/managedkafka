"""Server to provide GCP credentials to Kafka OAUTHBEARER protocol."""

import base64
import datetime
import http.server
import json

import google.auth
import google.auth.crypt
import google.auth.jwt
import google.auth.transport.urllib3
import urllib3


_credentials, _project = google.auth.default()
_http_client = urllib3.PoolManager()


def valid_credentials():
  if not _credentials.valid:
    _credentials.refresh(google.auth.transport.urllib3.Request(_http_client))
  return _credentials


_HEADER = json.dumps(dict(typ='JWT', alg='GOOG_OAUTH2_TOKEN'))


def get_jwt(creds):
  print('Creds ' + creds.service_account_email)
  return json.dumps(
      dict(
          exp=creds.expiry.timestamp(),
          iss='Google',
          iat=datetime.datetime.now(datetime.timezone.utc).timestamp(),
          scope='kafka',
          sub=creds.service_account_email,
      )
  )


def b64_encode(source):
  return (
      base64.urlsafe_b64encode(source.encode('utf-8'))
      .decode('utf-8')
      .rstrip('=')
  )


def get_kafka_access_token(creds):
  print('token: ' + creds.token)
  print('payload ' + b64_encode(get_jwt(creds)))
  return '.'.join(
      [b64_encode(_HEADER), b64_encode(get_jwt(creds)), b64_encode(creds.token)]
  )


def build_message():
  creds = valid_credentials()
  expiry_seconds = (
      creds.expiry - datetime.now(datetime.timezone.utc)
  ).total_seconds()
  return json.dumps(
      dict(
          access_token=get_kafka_access_token(creds),
          token_type='Bearer',
          expires_in=expiry_seconds,
      )
  )


class AuthHandler(http.server.BaseHTTPRequestHandler):
  """Handles HTTP requests for the GCP credentials server."""

  def _handle(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    message = build_message().encode('utf-8')
    print(message)
    self.wfile.write(message)

  def do_get(self):
    """Handles GET requests."""
    self._handle()

  def do_post(self):
    """Handles POST requests."""
    self._handle()


def run_server():
  server_address = ('localhost', 14293)
  server = http.server.ThreadingHTTPServer(server_address, AuthHandler)
  print(
      'Serving on localhost:14293. This is not accessible outside of the '
      'current machine.'
  )
  server.serve_forever()


if __name__ == '__main__':
  run_server()
