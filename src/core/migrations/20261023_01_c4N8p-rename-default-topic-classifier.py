"""Rename the default classifier without changing custom names or bot configuration."""

from yoyo import step


__depends__ = {"20261022_01_t7N4p-add-task-name"}

# No reverse rename: the original names cannot be recovered safely.
steps = [
    step(
        """
        UPDATE bot
        SET name = 'Topic Classifier'
        WHERE type = 'CYBERSEC_CLASSIFIER_BOT'
          AND name IN ('Cybersecurity Classifier Bot', 'Topic Classifier Bot');
        """
    ),
]
