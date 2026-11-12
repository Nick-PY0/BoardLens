"""Keep release identity stable across macOS builds without exporting keys."""
import re
import subprocess


def signing_identity(requested=None):
    if requested:
        return requested
    result = subprocess.run(
        ['/usr/bin/security', 'find-identity', '-v', '-p', 'codesigning'],
        capture_output=True, text=True, check=True)
    identities = re.findall(
        r'\b([A-Fa-f0-9]{40})\s+"Developer ID Application:[^"]+"', result.stdout)
    if len(identities) > 1:
        raise RuntimeError('Choose a Developer ID with --sign-identity; several are available.')
    # Public CI can still create an explicitly identified development build.
    # Its permissions do not carry over to a different ad hoc native build.
    return identities[0] if identities else '-'


def sign_app(app, identity):
    command = ['/usr/bin/codesign', '--force', '--sign', identity]
    if identity != '-':
        command.append('--timestamp')
    subprocess.run([*command, str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(app)], check=True)
    requirement = subprocess.check_output(
        ['/usr/bin/codesign', '-dr', '-', str(app)], stderr=subprocess.STDOUT, text=True)
    return {'kind': 'ad-hoc' if identity == '-' else 'developer-id',
            'requirement': requirement.strip()}
