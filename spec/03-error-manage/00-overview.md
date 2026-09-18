# Error Management Overview

## Core Philosophy
1. **Never Swallow Errors:** Every caught exception must be handled, wrapped, or logged. Bare `catch` or empty exception blocks are forbidden.
2. **Context on Catch:** Always log the operation name, file, and key parameters when capturing an error.
3. **Preserve Cause:** Wrap errors without losing the underlying stack trace or root exception.
4. **Universal Result Envelopes:** Prefer returning typed result structures (`Result[T]` or `{ data, errors, meta }`) over raw uncaught exceptions.
