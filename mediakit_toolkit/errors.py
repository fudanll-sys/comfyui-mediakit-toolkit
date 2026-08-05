"""Typed, user-facing errors raised by MediaKit Toolkit."""


class MediaKitError(RuntimeError):
    """Base class for errors safe to display in the ComfyUI node UI."""


class MediaKitDependencyError(MediaKitError):
    """A required local dependency is unavailable."""


class MediaKitConfigurationError(MediaKitError):
    """MediaKit credentials or configuration are invalid."""


class MediaKitInputError(MediaKitError):
    """An input media object cannot be consumed safely."""


class MediaKitCommandError(MediaKitError):
    """The MediaKit CLI failed or returned an invalid response."""


class MediaKitTaskError(MediaKitError):
    """A cloud task failed or did not return its expected output."""


class MediaKitCompatibilityError(MediaKitError):
    """The installed ComfyUI version lacks a required media API."""

