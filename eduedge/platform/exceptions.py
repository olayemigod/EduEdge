class EduEdgePlatformError(RuntimeError):
	"""Base error raised by the EduEdge platform adapter."""


class RemoteContractNotConfigured(EduEdgePlatformError):
	"""Raised when the central CoreEdge HTTP contract has not been configured."""


class RemotePlatformUnavailable(EduEdgePlatformError):
	"""Raised when the configured CoreEdge service cannot be reached."""


class RemoteResponseInvalid(EduEdgePlatformError):
	"""Raised when CoreEdge returns an invalid or unsafe payload."""


class RemoteAuthenticationFailed(EduEdgePlatformError):
	"""Raised when CoreEdge rejects the configured client identity."""
