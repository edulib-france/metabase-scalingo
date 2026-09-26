![Metabase](metabase.png)

# Deploying Metabase to Scalingo

## Deploying Using Scalingo's One-click Button

Click on the button below to deploy Metabase to Scalingo within minutes.

[![Deploy](https://cdn.scalingo.com/deploy/button.svg)](https://my.scalingo.com/deploy?source=https://github.com/Scalingo/metabase-scalingo#master)

## Deploying Using Scalingo's Command Line Tool

1. Create an application on Scalingo:

```bash
$ scalingo create my-metabase
```

2. Add a PostgreSQL for the internal usage of Metabase:

```bash
$ scalingo --app my-metabase addons-add postgresql postgresql-starter-512
```

3. Configure your application to use the appropriate buildpack for deployments:

```bash
$ scalingo --app my-metabase env-set 'BUILDPACK_URL=https://github.com/Scalingo/multi-buildpack'
```

4. Clone this repository:

```bash
$ git clone https://github.com/Scalingo/metabase-scalingo
```

5. Configure `git`:

```bash
$ cd metabase-scalingo
$ scalingo --app my-metabase git-setup
```

6. Deploy the application:

```bash
$ git push scalingo master
```

# Configuring the Application Deployment Environment

The following environment variables are available for you to adjust, depending
on your needs:

| Name                 | Description                                                                              | Default value                                   |
| -------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `BUILDPACK_URL`      | URL of the buildpack to use.                                                             | https://github.com/Scalingo/multi-buildpack.git |
| `DATABASE_URL`       | URL of your database addon. **Only available if you have a database addon provisioned**. | Provided by Scalingo                            |
| `MAX_METASPACE_SIZE` | Maximum amount of memory allocated to Java Metaspace[^1].                                | `512m` (512MB)                                  |

Metabase also [supports many environment variables](https://www.metabase.com/docs/latest/operations-guide/environment-variables.html).

[^1]: See https://wiki.openjdk.org/display/HotSpot/Metaspace for further details about Java Metaspace.

# Pinning the Metabase Version (Edulib)

The version deployed to `bi.edulib.fr` is pinned in
[`.metabase-version`](.metabase-version), which
[our buildpack](https://github.com/edulib-france/metabase-buildpack) reads at
build time. Keeping it in git rather than in the app's environment means the
deployed version is a reviewed diff, a rollback is a revert, and a bot can
watch it:

- **New releases**: Renovate opens a pull request bumping the file, with the
  release notes in the description. Merging it deploys, because the app
  auto-deploys from this repository. Only stable open-source releases are
  proposed: enterprise builds are versioned `1.x`, pre-releases are skipped
  (see [`renovate.json`](renovate.json)).
- **Known vulnerabilities**: every Monday, and on every change to the pinned
  version, [a workflow](.github/workflows/metabase-vulnerability-check.yml)
  asks NVD whether the pinned version is affected by a published CVE, and opens
  an issue when it is. It closes that issue once the version is no longer
  affected. Renovate cannot do this itself: Metabase is a jar downloaded from
  `downloads.metabase.com`, so it belongs to no package ecosystem the GitHub
  Advisory Database can match a version against.

Upgrading, then, is a one-line change to `.metabase-version`. Note that an
upgrade migrates Metabase's application database, which a downgrade does not
undo: restoring the previous version means restoring its database too.

In an emergency, setting `METABASE_VERSION` on the app overrides the file and
takes effect on the next deployment. Write the value back into the file
afterwards and remove the variable, or the file stops having any effect.

# Updating Metabase on Scalingo

To upgrade to the latest version of Metabase, you only need to redeploy it,
this will retrieve the latest version avaible on [the Metabase buildpack](https://github.com/metabase/metabase-buildpack).

## Updating After Deploying Using Scalingo's One-click Button

If you deployed your Metabase instance via our One-click button, you can update
it with the following command:

```bash
$ scalingo --app my-metabase deploy https://github.com/Scalingo/metabase-scalingo/archive/refs/heads/master.tar.gz
```

If you are facing the `create archive deployment: * git_ref → can't be blank` error, you may need to specify the version explicitly:

```bash
$ scalingo --app my-metabase deploy https://github.com/Scalingo/metabase-scalingo/archive/refs/heads/master.tar.gz v1.0.0
```

## Updating After Deploying Using Scalingo's Command Line Tool

```bash
$ cd metabase-scalingo
$ git pull origin master
$ git push scalingo master
```
