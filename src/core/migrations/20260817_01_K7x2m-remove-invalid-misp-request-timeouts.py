# pyright: reportMissingTypeStubs=false
"""Remove invalid MISP request timeout parameter values."""

from yoyo import step


__depends__ = {"20260710_01_m3P7q-add-product-last-published-url"}

steps = [
    step(
        """
        DELETE FROM parameter_value AS parameter
        WHERE parameter.parameter = 'REQUEST_TIMEOUT'
          AND parameter.value <> ''
          AND NOT (
              parameter.value ~ '^[[:space:]]*[+]?[0-9]+[[:space:]]*$'
              AND parameter.value ~ '[1-9]'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM worker_parameter_value AS worker_parameter
              WHERE worker_parameter.parameter_value_id = parameter.id
          )
          AND (
              EXISTS (
                  SELECT 1
                  FROM connector_parameter_value AS connector_parameter
                  JOIN connector ON connector.id = connector_parameter.connector_id
                  WHERE connector_parameter.parameter_value_id = parameter.id
                    AND connector.type = 'MISP_CONNECTOR'
              )
              OR EXISTS (
                  SELECT 1
                  FROM osint_source_parameter_value AS source_parameter
                  JOIN osint_source ON osint_source.id = source_parameter.osint_source_id
                  WHERE source_parameter.parameter_value_id = parameter.id
                    AND osint_source.type = 'MISP_COLLECTOR'
              )
          );
        """,
        "SELECT 1;",
    )
]
