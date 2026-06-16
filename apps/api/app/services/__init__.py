"""Service package.

Keep this module lightweight. Several service implementations depend on
optional runtime packages or external services, so callers should import the
concrete class they need from its module instead of relying on eager package
exports here.
"""
