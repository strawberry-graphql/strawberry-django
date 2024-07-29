---
title: Export Schema
---

# Export Schema

> [!INFO]
> The `export_schema` management command provided here is specifically designed for use with `strawberry_django`. The [default Strawberry export command](https://strawberry.rocks/docs/guides/schema-export) won't work with `strawberry_django` schemas because `strawberry_django` extends the base functionality of Strawberry to integrate with Django models and queries. This command ensures proper schema export functionality.

The `export_schema` management command allows you to export a GraphQL schema defined using the `strawberry_django` library. This command converts the schema definition to GraphQL schema definition language (SDL), which can then be saved to a file or printed to the console.

## Usage

To use the `export_schema` command, you need to specify the schema location(e.g., myapp.schema). Optionally, you can provide a file path to save the schema. If no path is provided, the schema will be printed to the console.

```sh
python manage.py export_schema <schema_location> --path <output_path>
```

### Arguments

- `<schema_location>`: The location of the schema module. This should be a dot-separated Python path (e.g., myapp.schema). For example, if your schema is located in the `schemas` directory in the `myapp` django app, you would use `myapp.schemas`.

### Options

- `--path <output_path>`: An optional argument specifying the file path where the schema should be saved. If not provided, the schema will be printed to standard output.

## Example

Here's an example of how to use the export_schema command:

```sh
python manage.py export_schema myapp.schema --path=output/schema.graphql
```

In this example, the schema located at `myapp.schema` will be exported to the file `output/schema.graphql`.
