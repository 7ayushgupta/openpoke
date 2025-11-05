Place your corporate root CA certificate here as a PEM file named `corporate-ca.pem`.

How to obtain:
- Export it from your enterprise SSL inspection/proxy solution or ask IT/SecOps for the root CA PEM.
- Ensure the file is in PEM format and includes the BEGIN/END CERTIFICATE markers.

Why this is needed:
- npm and Node do not always use the system keychain on macOS. Pointing to the corporate CA via `.npmrc` (cafile) and `NODE_EXTRA_CA_CERTS` allows TLS verification to remain enabled while trusting your company’s certificate chain.

