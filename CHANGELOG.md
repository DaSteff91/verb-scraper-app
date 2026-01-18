# CHANGELOG

<!-- version list -->

## v1.5.1 (2026-01-18)

### Bug Fixes

- Implementing containerization and push to ghcr and deploy on server
  ([`a8d7560`](https://github.com/DaSteff91/verb-scraper-app/commit/a8d756096be82ee4dee80381ea16c1fd7b1c280d))


## v1.5.0 (2026-01-18)

### Features

- **preparing-the-app-for-dockerization**: Making it ghcr ready
  ([`545c505`](https://github.com/DaSteff91/verb-scraper-app/commit/545c5056e427448f7a48eebf726c8208d3b6826f))


## v1.4.1 (2026-01-18)

### Bug Fixes

- Changing utf 8 format and normalizing white spaces in output fields with multiple scraped words
  ([`73c1cc1`](https://github.com/DaSteff91/verb-scraper-app/commit/73c1cc12f12d297176b82c24083bc94baaacc3f4))

- Fixing the exporter as well as implementing a switch for brasilian portugues conjugation format
  ([`4d76001`](https://github.com/DaSteff91/verb-scraper-app/commit/4d760012d9c5d6ffff3d7fc93869aca0f725eb76))

### Chores

- Adding the csv exporter to the project
  ([`71348c6`](https://github.com/DaSteff91/verb-scraper-app/commit/71348c6b7a1f31a3b343c54fa6b42cce00716a04))

- Manual sync of version to v1.4.0 and fix release config
  ([`4539aa9`](https://github.com/DaSteff91/verb-scraper-app/commit/4539aa98aa484383c3de1647171f50117f96f580))


## v1.4.0 (2026-01-18)

### Features

-
  **instead-of-4-making-all-6-conjugations-available,-gettting-the-UI-dynamic-and-focusing-scraping-only-on-subjuntivo-and-indicativo**:
  Implemented parent scoping in the scraper to get better h element scraping results plus adding
  some js into the html files
  ([`2344616`](https://github.com/DaSteff91/verb-scraper-app/commit/234461653eb38196cc6f72a0cc9547cb46d67dc8))


## v1.3.0 (2026-01-17)

### Bug Fixes

- **preparing-for-harmonizing-the-semversion-syncing**: Adding already a base html template for
  flask ui
  ([`7d909da`](https://github.com/DaSteff91/verb-scraper-app/commit/7d909da1f32caeca1d1166cf9cb8c344d5e7c9d7))

### Chores

- Manual sync of version to v1.2.0
  ([`b467a21`](https://github.com/DaSteff91/verb-scraper-app/commit/b467a2143891313f79eaa7b5a83fe46c47bf639e))

### Features

- **extending-functionality-and-getting-more-ui-stuff**: Adding files and changing something here
  and there
  ([`82a10dd`](https://github.com/DaSteff91/verb-scraper-app/commit/82a10ddcd538e19a33b70efdc49aae36163f148c))


## v1.2.0 (2026-01-17)

### Features

- **adding-the-first-main-route-and-deleting-the-old-placeholders**: Adding the first main route and
  deleting the old placeholders
  ([`fd54998`](https://github.com/DaSteff91/verb-scraper-app/commit/fd54998c61dc61e423ad2c5d7ddb3cf6368e6016))


## v1.1.0 (2026-01-17)

### Features

- **getting-the-database-populated-with-perfectly-scraped-conjugations**: Using a combination of
  encode_contents(), .split("<br>") and separator to do the job
  ([`2e7448f`](https://github.com/DaSteff91/verb-scraper-app/commit/2e7448f18c28ee4aa716789ba8b890dda7aef628))


## v1.0.0 (2026-01-17)

- Initial Release
