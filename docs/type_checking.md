# Type Checking Guide

## Overview

This document outlines the type checking standards and practices for the IOTA project. We use MyPy for static type checking with a gradual typing approach.

## Configuration

Our type checking is configured in `mypy.ini` with different strictness levels for different parts of the codebase:

- `server/app/*`: Strict mode with no untyped definitions allowed
- `scripts/*`: Medium strictness with type checking but allowing some untyped definitions
- `tests/*`: Relaxed mode focusing on basic type safety

## Common Issues and Solutions

### 1. Optional Types

Always explicitly handle `None` cases when working with `Optional` types:

```python
from typing import Optional

def get_user(user_id: Optional[str] = None) -> str:
    if user_id is None:
        return "default_user"
    return user_id
```

### 2. Collection Types

Use specific collection types instead of generic ones:

```python
# Instead of this:
from collections.abc import Collection
items: Collection[str] = ["a", "b"]

# Use this:
from typing import List
items: List[str] = ["a", "b"]
```

### 3. SQLAlchemy Types

Always use proper SQLAlchemy type annotations:

```python
from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped

class User:
    name: Mapped[str] = Column(String)  # Correct
    # name: Column = Column(String)  # Incorrect
```

### 4. Return Types

Avoid returning `Any` by specifying concrete return types:

```python
from typing import List, Dict, Any

# Instead of this:
def get_config() -> Any:
    return {"key": "value"}

# Use this:
def get_config() -> Dict[str, str]:
    return {"key": "value"}
```

## Gradual Typing Strategy

1. Start with core modules (`server/app/core/*`)
2. Move to API endpoints and database models
3. Add types to utility scripts
4. Finally, add types to tests

## Running Type Checks

Run MyPy with:

```bash
mypy server/app scripts tests
```

Or check specific files:

```bash
mypy path/to/file.py
```

## CI/CD Integration

Type checking is part of our CI/CD pipeline and pre-commit hooks. All pull requests must pass type checking before being merged.

## Tools and Resources

- [MyPy Documentation](http://mypy.readthedocs.io/)
- [Python Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [no_implicit_optional](https://github.com/hauntsaninja/no_implicit_optional) - Tool for upgrading codebase to explicit optional types
