# Migration Framework

To have reproducible environments, support rollbacks and that every change is only executed once, we use [Golang Migrate](https://github.com/golang-migrate/migrate/tree/master) as a migration framework.

See the following URL for installation instructions and basic commands:
<https://github.com/golang-migrate/migrate/tree/master/cmd/migrate>

See the following URL for the migration file format instructions:
<https://github.com/golang-migrate/migrate/blob/master/MIGRATIONS.md>

## Practicalities

### Initialisation

The migration framework initialises the database. Therefore, no database tables exist before running the migrate step in the docker compose.

### File name format

The migration file name format follows the suggestion in [MIGRATIONS.md](https://github.com/golang-migrate/migrate/blob/master/MIGRATIONS.md) to use a timestamp as version.

```
{version}_{title}.up.{extension}
{version}_{title}.down.{extension}
```

On Linux, you can retrieve the current timestamp by running: `date +%s`.

### Migration Path

The path `./migrate/data/migrations` is copied to the migrate container. Thus, the docker container only executes the migrations in this path.

The other path: `./migrate/data/not_supported_yet`, contains an example migration based on code comments about unfinished work from the initialise script. As the path is not mounted, the docker container does not execute migrations in that path. To try out the migrations move the files to `./migrate/data/migrations`.

### Configure migrate image

There are a few environment variables needed to run the migrate script.

| Name       | Requiered | Explenation                                          |
|------------|-----------|------------------------------------------------------|
| DB_USER    | Yes       | The username for the database                        |
| DB_PASS    | Yes       | The password for the user                            |
| DB_URL     | Yes       | URL or IP to the postgis database                    |
| DB_NAME    | No        | PostgreSQL database name, default `data`             |
| DB_PORT    | No        | Database port, default `5432`                        |
| ENABLE_SSL | No        | Weather to use ssl for connection, default `disable` |
