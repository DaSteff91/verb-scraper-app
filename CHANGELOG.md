# CHANGELOG

<!-- version list -->

## v1.13.0 (2026-01-19)

### Bug Fixes

- **fixing-some-content**: Adding lost stuff and new stuff in the readme
  ([`dc10fe4`](https://github.com/DaSteff91/verb-scraper-app/commit/dc10fe4725f9090341fd25ebfb70438647495e36))

### Features

- **add-new-job-based-data-scraping-logic-for-multi-scraping-via-api**: Create new methods and
  changes in existing code to support job based scraping as well as apply changes to the sql db
  ([`1e76c39`](https://github.com/DaSteff91/verb-scraper-app/commit/1e76c39bdd3efd5c4f1c169316793aea4597124b))

- **implement-asynchronous-batch-processing-with-job-status-tracking**: Refactor API to asynchronous
  "Restaurant Pager" architecture
  ([`385ff24`](https://github.com/DaSteff91/verb-scraper-app/commit/385ff244a6e9fc6ee6ad74665fd23f46db9fd83c))

- **implement-asynchronous-REST-API-v1-and-professional-error-handling**: - Added secure API v1 with
  header-based X-API-KEY authentication.
  ([`11469cc`](https://github.com/DaSteff91/verb-scraper-app/commit/11469cc7e34a6ec0f7901114f02908317da47c93))

- **implement-filtered-GET,-global-error-handling,-and-job-janitor**: Feat: finalize professional
  API robustness
  ([`d09954b`](https://github.com/DaSteff91/verb-scraper-app/commit/d09954b133297abc1b1390025def714c8acb9dcb))

-
  **implement-REST-API-v1-and-secure-configuration-layer---Added-header-based-API-key-authentication-using-the-decorator-pattern.---Implemented-GET-/verbs/<infinitive>-with-manual-5NF-to-JSON-serialization.---Added-POST-/scrape-and-POST-/batch-for-single-and-multi-threaded-scraping.---Implemented-"Fail-Fast"-validation-for-API_KEY-in-Config.---Maintained-lazy-loading-and-strictly-typed-function-signatures.**:
  Adding new files and routes that enable to reach the app via an api using an api key
  ([`173c144`](https://github.com/DaSteff91/verb-scraper-app/commit/173c144bb6081412febba07c4d65f40b30727918))


## v1.12.0 (2026-01-19)

### Features

- **changing-the-ui-following-good-practises-of-webdesign-with-mobile-first**: Adding css stylesheet
  and reworking all html pages accordingly
  ([`55e62bc`](https://github.com/DaSteff91/verb-scraper-app/commit/55e62bcd6c60e5a54da7a96f92bf3c363078dd5d))


## v1.11.0 (2026-01-18)

### Bug Fixes

- **fix-ux-issues**: Xcloak added
  ([`c52d51e`](https://github.com/DaSteff91/verb-scraper-app/commit/c52d51e609d82066d589a847739831d57d4e4ba7))

### Features

- **adding-a-redirect-to-a-summary-dashboard-after-bulk-craping**: Adding new functions and a new
  route
  ([`6ca1b90`](https://github.com/DaSteff91/verb-scraper-app/commit/6ca1b9088bc34a2e2a2cd3e258b341da584dc829))

- **adding-batch-processing-into-the-apps-processing-logic): - ThreadPoolExecutor(max_workers=3**:
  This runs up to 3 scrapes at a time. This is the "sweet spot" where you get a 3x speedup without
  overloading the SQLite database file or getting your IP blocked by the source website.
  ([`5edd9a2`](https://github.com/DaSteff91/verb-scraper-app/commit/5edd9a20459f275ffd3147cd6563df5561f6b94e))

- **adding-the-option-as-well-to-the-single-scraping-mode-that-you-can-choose-the-filename**: Adding
  buttons and input fields
  ([`829966f`](https://github.com/DaSteff91/verb-scraper-app/commit/829966fe8e50eec1284f62c154c781aff13b70df))

- **finalizing-the-download-page-incl-having-an-overview-as-accordien-menues**: - Refactored
  VerbManager with ThreadPoolExecutor for concurrent scraping.
  ([`13962bc`](https://github.com/DaSteff91/verb-scraper-app/commit/13962bc69d7fce387a56f16a3aced70e15434840))

- **finalizing-the-multi-scrape-logic**: O- rchestration Logic: The batch_scrape route now actually
  calls manager.process_batch(tasks). This means clicking "Execute Batch" now triggers the real
  threaded scraping process.
  ([`dfebb4f`](https://github.com/DaSteff91/verb-scraper-app/commit/dfebb4f37e5712aeb9a83b288b942fb703fb37de))

- **implementing-multiselect-option-for-scraping-as-well-as-adjusting-the-ui-to-fit-the-needs**:
  Basically adding more js via js alpine to outsource the memory usage to the users browser
  ([`4ec096f`](https://github.com/DaSteff91/verb-scraper-app/commit/4ec096f337dec3e80ef3c1e46e9410482edb48ac))


## v1.10.0 (2026-01-18)

### Features

- **implementing-lazy-loading-of-bs-and-the-exporter**: Replacing the place where the libraries are
  called to be imported from
  ([`2c64a4f`](https://github.com/DaSteff91/verb-scraper-app/commit/2c64a4f0fb895c5256cf1771aa8426e85cd5af4c))


## v1.9.0 (2026-01-18)

### Features

- **reduce-the-memory-footprint-of-the-containers-idle-consumtpion**: Replace pandas with csv
  library as well change the workers used for the containers tasks
  ([`84dc7d8`](https://github.com/DaSteff91/verb-scraper-app/commit/84dc7d81125f8c5140821d17a9db8c85d643a6de))


## v1.8.0 (2026-01-18)

### Bug Fixes

- **add-dummy-key**: Provide dummy secret key for CI runner
  ([`22d1a33`](https://github.com/DaSteff91/verb-scraper-app/commit/22d1a33d2cff1aba6846737fc6b0bab240a37d19))

- **add-dummy-key**: Provide dummy secret key for CI runner
  ([`6c92997`](https://github.com/DaSteff91/verb-scraper-app/commit/6c92997fa886767255686ee2bb7a71707de9b090))

### Features

- **adding-user-input-sanitation**: Implementing a regex to check the user input fits the expected
  format
  ([`d2c29bf`](https://github.com/DaSteff91/verb-scraper-app/commit/d2c29bf2783e1ef07dd7628f7f3456e8e6af64c4))

- **implement-strict-input-validation-and-normalization**: Implement a regex based approach
  ([`c945bdd`](https://github.com/DaSteff91/verb-scraper-app/commit/c945bdd6baf1279ff939ffa8c60e2203910df167))


## v1.7.1 (2026-01-18)

### Bug Fixes

- **adding-badges-to-the-readme**: Changes in the markdown
  ([`6ddbc0d`](https://github.com/DaSteff91/verb-scraper-app/commit/6ddbc0deb3f574dbeb3a917cca4e290cf79946cd))


## v1.7.0 (2026-01-18)

### Bug Fixes

- **finalizing-the-test-for-the-scraper**: Adding more simple test cases
  ([`1af40e1`](https://github.com/DaSteff91/verb-scraper-app/commit/1af40e1c917a872e3125766c76b91957fa486205))

- **fixing-tests**: Failure A: test_export_csv_route_no_data
  ([`e9a0d46`](https://github.com/DaSteff91/verb-scraper-app/commit/e9a0d4694c5715ab1e62846d47877f3373448f8a))

### Features

- **adding-tests-for-the-database-handling-and-the-model-layer**: One small change in the verb model
  due to deprication warning in the test
  ([`72f704b`](https://github.com/DaSteff91/verb-scraper-app/commit/72f704becd7cf2f8dcd6020104f47689e3e65f6a))

- **adding-the-first-unittest**: Providing a unittest for the scraper vs an offline sample
  ([`91557df`](https://github.com/DaSteff91/verb-scraper-app/commit/91557dfa97945511aff4831e8ca7f5355ca6b813))

- **finalizing-the-test-exporter-tests**: Adding some new tests and fixing a bug in the verb file
  ([`20c21af`](https://github.com/DaSteff91/verb-scraper-app/commit/20c21af8c04681ebf652dfda84c1d24f88533c9c))

- **finalizing-the-testsuite**: Adding new tests to ensure the scraped format matches the expected
  format of the app
  ([`e1397fd`](https://github.com/DaSteff91/verb-scraper-app/commit/e1397fd50d153376489b6f5ff37e17eb49846c38))

- **implementing-the-first-stuff-for-the-testing-environment-like-preparing-fixtures**: Starting
  ([`53a1310`](https://github.com/DaSteff91/verb-scraper-app/commit/53a1310fd47c81eb3af489d596017ec6ddc484ed))


## v1.6.0 (2026-01-18)

### Features

- **accidently-arlready-started-preparing-for-test-suite-implementation-on-main**: Next - move to
  feature branch for this
  ([`3915b4d`](https://github.com/DaSteff91/verb-scraper-app/commit/3915b4de0f07ddec78f935242d5aab01fa0a0103))


## v1.5.6 (2026-01-18)

### Bug Fixes

- **formating-in-md**: Formating the image implementation of the example
  ([`50e49a5`](https://github.com/DaSteff91/verb-scraper-app/commit/50e49a57cc21fe79d64a80c177f3c8f24013d0b1))


## v1.5.5 (2026-01-18)

### Bug Fixes

- **reworking-some-md-formating,-adding-example-image-to-readme**: Nothing
  ([`681d6df`](https://github.com/DaSteff91/verb-scraper-app/commit/681d6df8defb7396ad1dd846a143015d377d54e6))


## v1.5.4 (2026-01-18)

### Bug Fixes

- **adding-a-license-and-readme.md-file**: No code changes
  ([`82367a3`](https://github.com/DaSteff91/verb-scraper-app/commit/82367a3fdf0180e2723be9fe06f6d328d4f0f12e))


## v1.5.3 (2026-01-18)

### Bug Fixes

- **fix-directory-missmatch**: Fix directory missmatch
  ([`53eb9d4`](https://github.com/DaSteff91/verb-scraper-app/commit/53eb9d4bda24f1eede05f91f783077f4e01417fb))


## v1.5.2 (2026-01-18)

### Bug Fixes

- **fixing-again-the-versioning-sync-as-well-a-lowercase-issue-of-docker**: Fix versioning keys and
  docker image casing
  ([`2ac3961`](https://github.com/DaSteff91/verb-scraper-app/commit/2ac3961a38931dc90c236a5467104b95184cdcf1))


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
