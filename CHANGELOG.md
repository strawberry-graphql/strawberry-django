0.74.0 - 2026-01-17
-------------------

Add configurable `PAGINATION_MAX_LIMIT` setting to cap pagination requests, preventing clients from requesting unlimited data via `limit: null` or excessive limits.

This addresses security and performance concerns by allowing projects to enforce a maximum number of records that can be requested through pagination.

**Configuration:**

```python
STRAWBERRY_DJANGO = {
    "PAGINATION_MAX_LIMIT": 1000,  # Cap all requests to 1000 records
}
```

When set, any client request with `limit: null`, negative limits, or limits exceeding the configured maximum will be capped to `PAGINATION_MAX_LIMIT`. Defaults to `None` (unlimited) for backward compatibility, though setting a limit is recommended for production environments.

Works with both offset-based and window-based pagination.

This release was contributed by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/847

0.73.1 - 2026-01-09
-------------------

This release fixes a bug, which caused nested prefetch_related hints to get incorrectly merged
in certain cases.

This release was contributed by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/839

0.73.0 - 2026-01-04
-------------------

Nothing changed, testing the new release process using `autopub`.

0.72.2 - 2026-01-04
-------------------

Nothing changed, testing the new release process using `autopub`.

This release was contributed by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/837

0.72.0 - 2025-12-28
-------------------

## What's Changed
* feat: use the new type-friendly way to define scalars from Strawberry by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/832

0.71.0 - 2025-12-26
-------------------

## What's Changed
* feat: Add string-based lookups for UUID fields by @Akay7 in https://github.com/strawberry-graphql/strawberry-django/pull/829
* feat: make messages if there's assert_no_errors more verbose by @Akay7 in https://github.com/strawberry-graphql/strawberry-django/pull/828
* refactor: replace deprecated _enum_definition with __strawberry_definition__ (https://github.com/strawberry-graphql/strawberry-django/commit/9acb4b25aa5cae25243ac48c4f1c7287db1216cc)
* fix(filters): use StrawberryField for DjangoModelFilterInput to respect python_name (https://github.com/strawberry-graphql/strawberry-django/commit/a3d9f14b8be14ebe1d2eebaa2daeb4680016e6e7)

0.70.1 - 2025-12-08
-------------------

## What's Changed
* fix(input): use None as default for Maybe fields instead of UNSET by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/824

0.70.0 - 2025-12-06
-------------------

## What's Changed
* feat: add support for strawberry.Maybe type in mutations and filter processing by @deepak-singh in https://github.com/strawberry-graphql/strawberry-django/pull/805

0.69.0 - 2025-12-06
-------------------

## What's changed

* feat: use prefetch_related for FK with nested annotations (https://github.com/strawberry-graphql/strawberry-django/commit/a6b3f85f80064093137602d3bd79c8a525fbe9ca)

0.68.0 - 2025-12-03
-------------------

## What's Changed
* feat: declare support for django 6.0 by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/821
* docs: add comprehensive guides for production usage by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/810
* chore(examples): modernize examples with modular apps and current best practices by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/811
* docs: fix critical code example errors and typos by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/819

0.67.2 - 2025-11-23
-------------------

## What's changed

* fix: fix wrong total_count when using distinct on m2m/o2m relationships (ff1f016fbd95ddaa7cd76cd712a58ad460ca87df)

0.67.1 - 2025-11-22
-------------------

## What's Changed
* fix: fix n+1 regression with fragments and custom connections by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/809
* fix: docs by @wimble3 in https://github.com/strawberry-graphql/strawberry-django/pull/802

0.67.0 - 2025-10-18
-------------------

## What's Changed

Note: If you have a custom connection that defines a `resolve_connection` method, ensure that you have `**kwargs` in case you are not defining all possible keyword parameters.

* feat: Forward custom kwargs to relay connection resolver by @stygmate in https://github.com/strawberry-graphql/strawberry-django/pull/801

0.66.2 - 2025-10-15
-------------------

## What's changed

* fix: fix one extra broken future annotations with the new | syntax (https://github.com/strawberry-graphql/strawberry-django/commit/cb9df84f64755074e37ddbad5f11ef1e0eadfd23)

0.66.1 - 2025-10-14
-------------------

## What's Changed
* fix: fix broken future annotations with the new | syntax by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/800

0.66.0 - 2025-10-12
-------------------

## What's Changed
* feat: support for Python 3.14 and drop 3.9, which has reached EOL by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/795
* fix: fix debug toolbar integration to work with v6.0 by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/796
* fix: Fix typo in depecation message for order decorator by @zvyn in https://github.com/strawberry-graphql/strawberry-django/pull/785

0.65.1 - 2025-07-26
-------------------

## What's changed

* fix(field): prevent early ImportError on Field.type to break (https://github.com/strawberry-graphql/strawberry-django/commit/a353b4f376fce9fb3b4faf88a1f92bcad857ea49)

0.65.0 - 2025-07-20
-------------------

## What's Changed
* Relay pagination optimizations by @Kitefiko in https://github.com/strawberry-graphql/strawberry-django/pull/777

0.64.0 - 2025-07-19
-------------------

## What's changed

* feat: bump minimum Strawberry version to 0.276.2

0.63.0 - 2025-07-16
-------------------

## What's Changed
* fix: ensure dataclass's kwarg-only is specified to allow mixing fields (closes #768) by @axieum in https://github.com/strawberry-graphql/strawberry-django/pull/769
* fix: handle lazy filters and ordering in strawberry_django.connection by @rcybulski1122012 in https://github.com/strawberry-graphql/strawberry-django/pull/773
* docs: Fix minor typo "recommented". by @roelzkie15 in https://github.com/strawberry-graphql/strawberry-django/pull/775
* test: pytest-xdist for parallel testing by @roelzkie15 in https://github.com/strawberry-graphql/strawberry-django/pull/776

0.62.0 - 2025-06-16
-------------------

## What's Changed
* delete unused filters for creating mutations by @star2000 in https://github.com/strawberry-graphql/strawberry-django/pull/761
* fix: fix filters using lazy annotations by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/765
* Add support for AND/OR filters to be lists by @soby in https://github.com/strawberry-graphql/strawberry-django/pull/762

0.61.0 - 2025-06-08
-------------------

## What's Changed
* feat(security): disallow mutations without filters by @star2000 in https://github.com/strawberry-graphql/strawberry-django/pull/755
* fix(ordering): fix lazy types in ordering by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/759

0.60.0 - 2025-05-24
-------------------

## What's Changed
* fix(optimizer): Pass accurate "info" parameter to PrefetchCallable and AnnotateCallable by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/742
* feat: wrap resolvers in `django_resolver(...)` to ensure appropriate async/sync context by @axieum in https://github.com/strawberry-graphql/strawberry-django/pull/746

0.59.1 - 2025-05-06
-------------------

## What's Changed
* fix: Fix "ordering" for connections and offset_paginated by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/741

0.59.0 - 2025-04-30
-------------------

## Highlights

This release brings some very interesting features, thanks to @diesieben07 🍓
- A new ordering type is now available, created using `⁠@strawberry_django.order_type`. This type uses a list for specifying ordering criteria instead of an object, making it easier and more flexible to apply multiple orderings, ensuring they will keep their order. Check the [ordering docs](https://strawberry.rocks/docs/django/guide/ordering) for more info on how to use it
- Support for "true" cursor-based pagination in connections, using the new `DjangoCursorConnection` type. Check the [relay docs](https://strawberry.rocks/docs/django/guide/relay#cursor-based-connections) for more info on how to use it

Also, to maintain consistency across the codebase, we have renamed several classes and functions. The old names are still available for import and use, making this a non-breaking change, but they are marked as deprecated and will eventually be removed in the future. The renames are as follows:

- `ListConnectionWithTotalCount` got renamed to `DjangoListConnection`
- `strawberry_django.filter` got renamed to `strawberry_django.filter_type`

## What's Changed
* feat: Add new ordering method allowing ordering by multiple fields by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/679
* feat: Add support for "true" cursor based pagination in connections by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/730
* refactor: rename ListConnectionWithTotalCount and filter for consistency by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/739
* fix: Fix duplicate LOOKUP_SEP being used when field hints are used with polymorphic queries by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/736
* fix: Fix a minor typing issue by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/738
* docs: Fix resolvers.md by @Hermotimos in https://github.com/strawberry-graphql/strawberry-django/pull/735

0.58.0 - 2025-04-04
-------------------

## What's Changed
* feat: Official Django 5.2 support by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/728
* feat: Improve handling of polymorphism in the optimizer by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/720
* fix: Compatibility with Django Debug Toolbar 5.1+ by @cpontvieux-systra in https://github.com/strawberry-graphql/strawberry-django/pull/725
* fix: Ensure max_results is consistently applied for connections by @Mapiarz in https://github.com/strawberry-graphql/strawberry-django/pull/727
* chore: Update mutations.py to expose the full_clean parameter by @keithhackbarth in https://github.com/strawberry-graphql/strawberry-django/pull/701

0.57.1 - 2025-03-22
-------------------

## What's Changed
* Improve fallback primary key ordering unit tests by @SupImDos in https://github.com/strawberry-graphql/strawberry-django/pull/716
* Fix unnecessary window pagination being used by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/719

0.57.0 - 2025-03-02
-------------------

## What's Changed
* Order unordered querysets by primary key by @SupImDos in https://github.com/strawberry-graphql/strawberry-django/pull/715

0.56.0 - 2025-02-16
-------------------

## What's Changed
* Add support for the the general `Geometry` type by @shmoon-kr in https://github.com/strawberry-graphql/strawberry-django/pull/709

0.55.2 - 2025-02-12
-------------------

## What's Changed
* Move `django-tree-queries` dependency to dev (it was wrongly added to main dependencies) (https://github.com/strawberry-graphql/strawberry-django/commit/fec457e589646dc4790f80c67286da714871a81c)

0.55.1 - 2025-01-26
-------------------

## What's Changed
* docs: fix inverted link tags by @pbratkowski in https://github.com/strawberry-graphql/strawberry-django/pull/692
* docs: fix typo by @ticosax in https://github.com/strawberry-graphql/strawberry-django/pull/696
* fix: omit TestClient from pytest's test discovery by @pbratkowski in https://github.com/strawberry-graphql/strawberry-django/pull/694
* fix(optimizer): Avoid merging prefetches when using aliases by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/698

0.55.0 - 2025-01-12
-------------------

## What's Changed
* feat: Allow setting max_results for connection fields by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/689

0.54.0 - 2025-01-09
-------------------

## What's Changed
* feat: Bump strawberry minumum version to 0.257.0, which contains a fix for https://github.com/strawberry-graphql/strawberry/security/advisories/GHSA-5xh2-23cc-5jc6 by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/688

0.53.3 - 2025-01-07
-------------------

## What's changed

* fix(mutations): Make sure we skip refetch when the optimizer is disabled (https://github.com/strawberry-graphql/strawberry-django/commit/06f62c74a37fc20d3122e7528add8e6c6119e591)

0.53.2 - 2025-01-07
-------------------

## What's Changed
* fix: skip empty choice value when generating enums from choices by @fabien-michel in https://github.com/strawberry-graphql/strawberry-django/pull/687
* test: Replace django mptt with django tree queries for tests by @kwongtn in https://github.com/strawberry-graphql/strawberry-django/pull/684

0.53.1 - 2025-01-03
-------------------

## What's Changed
* fix(optimizer): Fix nested pagination optimization for m2m relations by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/681
* Update test scope to include django 5.1 by @kwongtn in https://github.com/strawberry-graphql/strawberry-django/pull/683

0.53.0 - 2024-12-21
-------------------

## What's Changed
* Support multi-level nested create/update with model `full_clean()` by @philipstarkey in https://github.com/strawberry-graphql/strawberry-django/pull/659

0.52.1 - 2024-12-18
-------------------

## What's Changed
* fix(optimizer): Prevent issuing duplicated queries for certain uses of first() and get() by @diesieben07 in https://github.com/strawberry-graphql/strawberry-django/pull/675

0.52.0 - 2024-12-15
-------------------

## What's Changed
* fix(pagination)!: Use `PAGINATION_DEFAULT_LIMIT` when limit is not provided by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/673
* fix(mutations): Refetch instances to optimize the return value by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/674

0.51.0 - 2024-12-08
-------------------

## What's Changed
* Fix Django permissions diagram syntax by @sersorrel in https://github.com/strawberry-graphql/strawberry-django/pull/663
* allow FullCleanOptions in full_clean arg annotation by @g-as in https://github.com/strawberry-graphql/strawberry-django/pull/667
* Forward metadata when processing django type by @g-as in https://github.com/strawberry-graphql/strawberry-django/pull/666
* Added missing unpacking of strawberry.LazyType to optimzer.py by @NT-Timm in https://github.com/strawberry-graphql/strawberry-django/pull/670
* Improved language in mutations docs by @KyeRussell in https://github.com/strawberry-graphql/strawberry-django/pull/668
* Batch Mutations for creating, updating, and deleting #438 by @keithhackbarth in https://github.com/strawberry-graphql/strawberry-django/pull/653
* docs: fix import typo by @lozhkinandrei in https://github.com/strawberry-graphql/strawberry-django/pull/661
* docs: Fix incorrect import paths in faq.md by @videvide in https://github.com/strawberry-graphql/strawberry-django/pull/669

0.50.0 - 2024-11-09
-------------------

## What's Changed
* feat: New Paginated generic to be used as a wrapped for paginated results by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/642 (learn how to use it [in the docs page](https://strawberry.rocks/docs/django/guide/pagination#offsetpaginated-generic))
* Update filtering caution in mutations.md by @ldynia in https://github.com/strawberry-graphql/strawberry-django/pull/648
* update model_property path in the doc by @alainburindi in https://github.com/strawberry-graphql/strawberry-django/pull/654

0.49.1 - 2024-10-19
-------------------

## What's Changed
* docs: Remove mention about having to enable subscriptions in the docs by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/645
* Add unit tests for partial input optional field behaviour in update mutations by @SupImDos in https://github.com/strawberry-graphql/strawberry-django/pull/638
* fix: Make sure that async fields always return Awaitables by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/646

0.49.0 - 2024-10-17
-------------------

## What's Changed
* feat: Official support for Python 3.13 and drop support for Python 3.8 which has reached EOL by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/643
* Changed the recommended library for JWT Authentication in Django to strawberry-django-auth by @pkrakesh in https://github.com/strawberry-graphql/strawberry-django/pull/633

0.48.0 - 2024-09-24
-------------------

## What's Changed
* Change default Relay input m2m types from `ListInput[NodeInputPartial]` to `ListInput[NodeInput]` by @SupImDos in https://github.com/strawberry-graphql/strawberry-django/pull/630
* refactor: Remove guardian ObjectPermissionChecker monkey patch by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/631

0.47.2 - 2024-09-04
-------------------

## What's Changed
* Fix calculation of `has_next_page` in `resolve_connection_from_cache` by @SupImDos in https://github.com/strawberry-graphql/strawberry-django/pull/622
* Update docs for main website by @patrick91 in https://github.com/strawberry-graphql/strawberry-django/pull/605
* docs: Update docs URLs to point to the new location by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/606
* docs: General doc improvements by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/610

0.47.1 - 2024-07-24
-------------------

## What's Changed
* fix: Fix debug toolbar upgrade issue by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/600
* fix: Only set False to clear FileFields when updating an instance by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/601

0.47.0 - 2024-07-18
-------------------

## What's Changed
* feat: Bump strawberry to [0.236.0](https://github.com/strawberry-graphql/strawberry/releases/tag/0.236.0) and refactor changed imports by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/591

0.46.2 - 2024-07-14
-------------------

## What's Changed
* refactor(optimizer): Split optimizer code to make it cleaner and easier to understand/maintain by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/575
* fix(optimizer): Convert select_related into Prefetch when the type defines a custom get_queryset by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/583
* fix(optimizer): Avoid extra queries for prefetches with existing prefetch hints by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/582
* fix: Do not try to call an ordering object's `order` method if it is not a decorated method by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/584
* fix: Avoid pagination failures when filtering connection by last without before/after by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/585

0.46.1 - 2024-06-30
-------------------

## What's Changed
* fix: Fix and test optimizer with polymorphic relay node by @stygmate in https://github.com/strawberry-graphql/strawberry-django/pull/570
* fix: Fix nested pagination/filtering/ordering not working when "only optimization" is disabled by @aprams in https://github.com/strawberry-graphql/strawberry-django/pull/569

0.46.0 - 2024-06-29
-------------------

## What's Changed
* feat: Add support for auto mapping of ArrayFields by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/567
* fix: Set files early on mutations to allow clean methods to validate them by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/566
* fix: Make sure the optimizer calls the type's `get_queryset` for nested lists/connections by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/568

0.45.0 - 2024-06-27
-------------------

## What's Changed
* Generated fields type resolution by @Mapiarz in https://github.com/strawberry-graphql/strawberry-django/pull/565

0.44.2 - 2024-06-17
-------------------

## What's Changed
* docs: wrong typo on filter on fruitfilter by @OdysseyJ in https://github.com/strawberry-graphql/strawberry-django/pull/555
* docs: Remove officially unmaintained project by @Eraldo in https://github.com/strawberry-graphql/strawberry-django/pull/557
* test: Add some tests to ensure Interfaces can be properly optimized by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/554
* fix: Extract interface definition in optimizer to fix django-polymorphic by @ManiacMaxo in https://github.com/strawberry-graphql/strawberry-django/pull/556

0.44.1 - 2024-06-12
-------------------

## What's Changed
* fix: fix optimized nested connections failing to access totalCount by @bellini666 and @Eraldo in https://github.com/strawberry-graphql/strawberry-django/pull/553

0.44.0 - 2024-06-10
-------------------

## What's Changed

* feat: Nested optimization for lists and connections by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/540

This releases finally enables the highly anticipated nested optimization for lists and connections 🚀

What does that mean? Remember that when trying to retrieve a relation list inside another type and also trying to filter/order/paginate, that would cause n+1 issues because it would force the prefetched list to be thrown away? Well, not anymore after this release! 😊

In case you find any issues with this, please let us know by registering an issue with as much information as possible on how to reproduce the issue.

Note that even though this is enabled by default, nested optimizations can be disabled by passing `enabled_nested_relations_prefetch=False` when initializing the optimizer extensions.

* Dropped support for Django versions earlier than 4.2

The nested optimization feature required features only available on Django 4.2+.

To be able to implement it, and also considering that [django itself recommended dropping support for those versions](https://docs.djangoproject.com/en/5.0/releases/5.0/#third-party-library-support-for-older-version-of-django), from now on this lib requires Django 4.2+

0.43.0 - 2024-06-07
-------------------

## What's Changed
* Added `export-schema` command to Docs by @Ckk3 in https://github.com/strawberry-graphql/strawberry-django/pull/546
* fix: Fix specialized connection aliases missing filters/ordering by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/547

NOTE: Even though this only contains a bug fix, I decided to do a minor release because the fix is bumping the minimum required version of `strawberry-graphql` itself to 0.234.2.

0.42.0 - 2024-05-30
-------------------

## What's Changed
* refactor: Use graphql-core's collect_sub_fields instead of our own implementation by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/537

0.41.1 - 2024-05-26
-------------------

## What's changed

* fix: Move Info out of the TYPE_CHECKING block to prevent a warning (https://github.com/strawberry-graphql/strawberry-django/commit/4e8c458b1a6c546af705e797d80edf48ca74d693)

0.41.0 - 2024-05-26
-------------------

## What's Changed
* docs: Fix typo by @Eraldo in https://github.com/strawberry-graphql/strawberry-django/pull/531
* feat: Add setting DEFAULT_PK_FIELD_NAME by @noamsto in https://github.com/strawberry-graphql/strawberry-django/pull/446
* fix: Fix AttributeError when using optimizer and prefetch_related by @jacobwegner in https://github.com/strawberry-graphql/strawberry-django/pull/533

0.40.0 - 2024-05-11
-------------------

## What's Changed
* feat: Avoid calling Type.get_queryset method more than once by @bellini666 in (https://github.com/strawberry-graphql/strawberry-django/commit/690551374053760903d70c6d267e73a64c6ad282)
* test(listconnectionwithtotalcount): check the number of SQL queries when only fetching totalCount by @euriostigue in https://github.com/strawberry-graphql/strawberry-django/pull/525
* fix(optimizer): handle existing select_related in querysets by @taobojlen in https://github.com/strawberry-graphql/strawberry-django/pull/515

0.39.2 - 2024-04-25
-------------------

## What's Changed
* fix: Delete mutation should not throw error if no objects in filterset by @keithhackbarth in https://github.com/strawberry-graphql/strawberry-django/pull/522

0.39.1 - 2024-04-21
-------------------

## What's changed

* fix: fix annotations inheritance override for python 3.8/3.9

0.39.0 - 2024-04-21
-------------------

## What's changed

* feat: support for strawberry 0.227.1+

0.38.0 - 2024-04-20
-------------------

## What's Changed
* feat: Ability to use custom field_cls for connections and nodes (#517)
* Fix typos in filtering documentation by @cdroege in https://github.com/strawberry-graphql/strawberry-django/pull/520

0.37.1 - 2024-04-14
-------------------

## What's Changed
* Fixing Docs Typo by @drewbeno1 in https://github.com/strawberry-graphql/strawberry-django/pull/513
* fix: fix debug toolbar when used with apollo_sandbox ide (#514)
* fix: fix debug toolbar running on ASGI and Python 3.12

0.37.0 - 2024-04-01
-------------------

## What's Changed
* feat: filter_field optional value resolution by @Kitefiko in https://github.com/strawberry-graphql/strawberry-django/pull/510

0.36.0 - 2024-03-30
-------------------

## What's Changed
* feat: properly resolve `_id` fields to `ID` (https://github.com/strawberry-graphql/strawberry-django/issues/506)

0.35.1 - 2024-03-19
-------------------

## What's Changed
* fix: async with new filter API (assert queryset is wrong) by @devkral in https://github.com/strawberry-graphql/strawberry-django/pull/504

0.35.0 - 2024-03-18
-------------------

## 🚀  Highlights (contains **BREAKING CHANGES**)

This release contains a major refactor of how filters and ordering works with this library (https://github.com/strawberry-graphql/strawberry-django/pull/478).

Thank you very much for this excellent work @Kitefiko 😊

Some distinctions between the new API and the old API:

### Filtering

* The previously deprecated `NOT` filters with a leading `n` were removing, `NOT` is the only negation option from now on
* New `DISTINCT: Boolean` option to call `.distinct()` in the resulting QuerySet: https://strawberry-graphql.github.io/strawberry-django/guide/filters/#and-or-not-distinct
* Custom filters can be defined using a method with the `@strawberry_django.filter_field` decorator: https://strawberry-graphql.github.io/strawberry-django/guide/filters/#custom-filter-methods
* The default filter method can be overriden also by using a `@strawberry_django.filter_field` decorator: https://strawberry-graphql.github.io/strawberry-django/guide/filters/#overriding-the-default-filter-method
* Lookups have been separated into multiple types to make sure the API is not exposing an invalid lookup for a given attribute (e.g. trying to filter a `BooleanField` by `__range`): https://strawberry-graphql.github.io/strawberry-django/guide/filters/#generic-lookup-reference

**_IMPORTANT NOTE_**: If you find any issues and/or can't migrate your codebase yet, the old behaviour can still be achieved by setting `USE_DEPRECATED_FILTERS=True` in your django settings: https://strawberry-graphql.github.io/strawberry-django/guide/filters/#legacy-filtering

Also, make sure to [report any issues](https://github.com/strawberry-graphql/strawberry-django/issues/new/choose) you find with the new API.

### Ordering

* It is now possible to define custom ordering methods: https://strawberry-graphql.github.io/strawberry-django/guide/ordering/#custom-order-methods
* The `Ordering` enum have 4 more options: `ASC_NULLS_FIRST`, `ASC_NULLS_LAST`, `DESC_NULLS_FIRST` and `DESC_NULLS_LAST`: https://strawberry-graphql.github.io/strawberry-django/guide/ordering/#ordering
* The default order method can now be overridden for the entire resolution: https://strawberry-graphql.github.io/strawberry-django/guide/ordering/#overriding-the-default-order-method

There are no breaking changes in the new ordering API, but please [report any issues](https://github.com/strawberry-graphql/strawberry-django/issues/new/choose) you find when using it.

0.34.0 - 2024-03-16
-------------------

## What's Changed
* Fix `_perm_cache` processing by @vecchp in https://github.com/strawberry-graphql/strawberry-django/pull/498
* feat: Add support for generated enums in mutation input by @cngai in https://github.com/strawberry-graphql/strawberry-django/pull/497

0.33.0 - 2024-03-05
-------------------

## What's Changed
* chore: update and improve github workflows by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/492
* fix: use str() to trigger eventual django's gettext_lazy string by @fabien-michel in https://github.com/strawberry-graphql/strawberry-django/pull/493
* Fix auto enum value allowed chars by @fabien-michel in https://github.com/strawberry-graphql/strawberry-django/pull/494

0.32.2 - 2024-02-27
-------------------

## What's Changed
* Add py.typed marker for mypy by @pm-incyan in https://github.com/strawberry-graphql/strawberry-django/pull/486
* fix: OneToManyInput saves and runs validation on foreign key #487 by @keithhackbarth in https://github.com/strawberry-graphql/strawberry-django/pull/490

0.32.0 - 2024-02-19
-------------------

## What's Changed
* Expose pagination api publicly by @fireteam99 in https://github.com/strawberry-graphql/strawberry-django/pull/476
* Fix permissioned pagination by @vecchp in https://github.com/strawberry-graphql/strawberry-django/pull/480
* feat: allow extensions to prevent results from being fetched by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/481

0.31.0 - 2024-02-07
-------------------

## What's Changed
* chore: Rename all links to the new repository name by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/477
* fix: cache definitions in optimizer by @yergom in https://github.com/strawberry-graphql/strawberry-django/pull/474

0.30.1 - 2024-02-05
-------------------

## What's Changed
* validate files at dummy-instance level by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/469

0.30.0 - 2024-01-27
-------------------

## What's Changed
* fix: fix files not being saved on create mutation by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/464
* feat(optimizer): Do not defer select_related fields if no only was specified by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/465
* fix: Return `null` on empty files/images by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/466

0.29.0 - 2024-01-23
-------------------

## What's Changed
* Documentation improvements by @thclark in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/456
* fix(docs): Add missing import to resolver snippet by @lewisjared in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/457
* Allow updates of nested fields by @tokr-bit in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/449

0.28.3 - 2023-12-23
-------------------

## What's Changed
* fix(docs): Standardising the use of strawberry_django throughout the documentation. by @ArcD7 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/440
* Fix code example on updating `field_type_map`. by @alimony in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/441
* fix: support for fields using async only extensions by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/444

0.28.2 - 2023-12-08
-------------------

## What's Changed
* fix: HasPerm on async fields, fix missing query in another test by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/437
* fix(docs): resolvers.md strawberry_django import by @hkfi in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/436

0.28.1 - 2023-12-06
-------------------

## What's Changed
* fix: really push OR, AND and NOT to the end by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/435

0.28.0 - 2023-12-06
-------------------

## What's changed

* Official support for Django 5.0

0.27.0 - 2023-12-04
-------------------

## What's Changed
* Fix: ordering when dealing with camelCased field by @he0119 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/430
* Guarantee 'AND', 'OR', and 'NOT' filter fields get evaluated last by … by @TWeidi in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/424

0.26.0 - 2023-11-29
-------------------

## What's Changed
* Login and CurrentUser queries yield broken responses by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/421

0.25.0 - 2023-11-18
-------------------

## What's Changed
* fix small errata by @jalvarezz13 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/419
* Refactor create method to ensure proxy-model compatibility by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/394

0.24.4 - 2023-11-17
-------------------

## What's Changed
* Fix typing issues by @patrick91 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/418

0.24.3 - 2023-11-15
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/416
* perf: cache nested import of get_user_or_annonymous to improve performance by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/417

0.24.2 - 2023-11-13
-------------------

## What's Changed
* fix: make sure custom fields are kept during inheritance by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/415

0.24.1 - 2023-11-07
-------------------

## What's Changed
* fix: Use _RESOLVER_TYPE as the type for the resolver on field, so the… by @guizesilva in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/412

0.24.0 - 2023-11-07
-------------------

## What's Changed
* feat: Enforce validation for updating nested relations by @tokr-bit in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/405
* feat: support for strawberry 0.212.0+ by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/410

0.23.0 - 2023-11-05
-------------------

## What's Changed
* docs: Fix typos in optimization examples by @sjdemartini in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/406
* docs: Fix typos in object-level Permissions documentation by @sjdemartini in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/407
* fix: keep ordering sequence by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/409

0.22.0 - 2023-10-30
-------------------

## What's Changed
* Fixed Documentation issue #390: added explanation of the error and PYTHON_CONFIGURE_OPTS: a little bit verbose, but maybe will save someone time and possibly add contributors to the project by @thepapermen in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/392
* docs: Added strawberry-django-extras to community-projects.md by @m4riok in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/395
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/400
* chore: migrate from black to ruff-formatter by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/403
* compatibility ASGI/websockets get_request, login and logout by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/393

0.21.0 - 2023-10-11
-------------------

## What's Changed
* chore: Update docs to include changes to partial behavior by @whardeman in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/385
* Docs improvement Subscriptions by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/376
* New Feature: Optional custom key_attr to that can be used instead of id (pk) in to access model in Django UD mutations (Issue #348) by @thepapermen in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/387

0.20.3 - 2023-10-09
-------------------

## What's changed

* fix: fix a regression when checking permissions for an async resolver

0.20.2 - 2023-10-09
-------------------

## What's changed

* fix: ensure permissions' resolve_for_user get safely resolved inside async contexts

0.20.1 - 2023-10-06
-------------------

## What's Changed
* FIX: DEBUG_TOOLBAR_CONFIG consideration by @bpeterman in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/384

0.20.0 - 2023-10-02
-------------------

## What's Changed
* feat: support for python 3.12 by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/359

0.19.0 - 2023-10-01
-------------------

## What's Changed
* feat: deprecate nSomething in favor of using NOT by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/381
* Fix: DjangoOptimizerExtension corrupts nested objects' fields' prefetch objects by @aprams in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/380

0.18.0 - 2023-09-28
-------------------

## What's Changed
* Support annotate parameter in field to allow ORM annotations by @fjsj in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/377

0.17.4 - 2023-09-25
-------------------

## What's Changed
* Exclude id from model fields to avoid overriding the id: type by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/373

0.17.3 - 2023-09-21
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/365
* Update relay.md to working example by @sdobbelaere in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/368
* Expose disable_optimization argument on by @Mapiarz in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/370

0.17.2 - 2023-09-15
-------------------

## What's Changed
* Support inList and nInList lookup in filters on enum by @cpontvieux-systra in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/363

0.17.1 - 2023-09-12
-------------------

## What's Changed
* fix: Update related objects with unique_together by @zvyn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/362

0.17.0 - 2023-09-11
-------------------

## What's Changed
* feat: Add ValidationError code to OperationMessage by @zvyn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/358
* Docs on Mutations: Fixed issue with relay.NodeInput not existing, imported NodeInput from strawberry_django instead by @thepapermen in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/353
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/355
* docs: fix sample code on 'Serving the API' by @miyashiiii in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/357

0.16.1 - 2023-08-31
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/332
* Fix typo in optimizer docs for `strawberry.django.type` annotation by @fireteam99 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/334
* Adds tip regarding automatic single query filter generation to docs by @fireteam99 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/341
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/342
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/350
* refactor: strawberry.union is deprecated, use `Annotated` instead by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/347
* Unwrap django lazy objects in mutation resolvers by @ryanprobus in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/338

0.16.0 - 2023-08-02
-------------------

## What's Changed
* feat: support strawberry 0.199.0+ by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/326

0.15.0 - 2023-07-31
-------------------

## What's changed

* feat: drop python 3.7 support, which EOLed on June 2023, following strawberry's 0.198.0 release
* refactor: make sure to not insert duplicate permission directives to the field

0.14.1 - 2023-07-29
-------------------

## What's Changed
* refactor: make sure to also call the type's get_queryset when retrieving nodes for connection or a list of nodes
* Update mutations.md by @baseplate-admin in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/319
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/321

0.14.0 - 2023-07-19
-------------------

## What's Changed
* filters support 'NOT' 'AND' 'OR' by @star2000 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/313
* feat: make sure to run the type's `get_queryset` when one is defined on resolve_model_node (#316)

0.13.1 - 2023-07-19
-------------------

## What's Changed
* Fix TypeError with IntegerChoices and Add Tests for Enum Conversion without django_choices_field by @miyashiiii in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/314

0.13.0 - 2023-07-17
-------------------

## What's Changed
* docs: change one occurence of select_related to prefetch_related by @Wartijn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/306
* fix: fix an issue where non dataclass annotations where being injected as fields on input types by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/310
* Add new keywords "fields" and "exclude" to type decorator for auto-population of Django model fields by @coleshaw in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/293
* fix: fix resolving optional fields based on reverse one-to-one relations by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/309
* fix: default pagination/filters/order to UNSET for fields (#257)

0.12.0 - 2023-07-13
-------------------

## What's Changed
* refactor!: use a setting to decide if we should map fields to relay types or not by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/302

NOTE: If you are using relay integration in all your types, you probably will want to set `MAP_AUTO_ID_AS_GLOBAL_ID=True` in your [strawberry django settings](https://strawberry-graphql.github.io/strawberry-graphql-django/guide/settings/) to make sure `auto` gets mapped properly to `GlobalID` on types and filters.

0.11.0 - 2023-07-12
-------------------

## What's Changed
* feat: add command export schema by @menegasse in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/299
* feat: expose `interface` on strawberry_django/__init__.py by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/300

0.10.7 - 2023-07-12
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/291
* fix: pass **kwargs to the type's `get_queryset` when defined by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/295
* Fix missing model docstring crash by @Mapiarz in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/297
* docs: update absolute path to relative in markdown file by @miyashiiii in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/296

0.10.6 - 2023-07-10
-------------------

## What's Changed
* Fixed typo __dic__ by @selvarajrajkanna in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/290

0.10.5 - 2023-07-08
-------------------

## What's Changed
* Handle Django GENERATE_ENUMS_FROM_CHOICES with strawberry.auto by @pcraciunoiu in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/286

0.10.4 - 2023-07-08
-------------------

## What's Changed
* docs: tweak links to work with non-root path for hosting by @DavidLemayian in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/283
* Typo fix in documentation by @paltman in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/285
* Remove usage of `concrete_of` by @patrick91 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/287

0.10.3 - 2023-07-06
-------------------

## What's changed

* fix: make sure field_name overriding is not ignored when querying data (#282)
* fix: the type's queryset doesn't receive **kwarg
* fix: make sure the type's get_queryset gets called for resolved coroutines (#281)
* chore: expose missing input_mutation in __init__ file
* docs: fix some documentation examples

0.10.2 - 2023-07-05
-------------------

## What's Changed
* fix: reset annotation cache to fix some inheritance issues when using `strawberry>=0.192.2` by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/278

0.10.1 - 2023-07-05
-------------------

## What's Changed
* fix: do not import anything from `strawberry.django` that is not in this lib by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/277

0.10.0 - 2023-07-05
-------------------

## Highlights

This release is a major milestone for strawberry-django. Here are some of its highlights:

* The [strawberry-django-plus](https://github.com/blb-ventures/strawberry-django-plus) lib was finally [merged](https://github.com/strawberry-graphql/strawberry-graphql-django/issues/139) into this lib, meaning all the extra features it provides are available directly in here. strawberry-django-plus is being deprecated and the development of its features is going to continue here. Here is a quick summary of all the features ported from it:
  * The query optimizer extension
  * The relay integration (based on the new official relay support from strawberry)
  * Enum integration with [django-choices-field](https://github.com/bellini666/django-choices-field) and auto generation from fields with choices
  * Lots of improvements to mutations, allowing CUD mutations to handle nested creation/updating/etc
  * The permissioned resolvers, designed as field extensions now instead of the custom schema directives it used
* All the API has been properly typed, meaning that type checkers should be able to properly validate calls to `strawberry_django.type(...)`/`strawberry_django.field(...)`/etc
* The [docs](https://strawberry-graphql.github.io/strawberry-graphql-django/) have been updated with all the new features
* A major performance improvement: Due to all the refactoring and improvements, some personal benchmarks show a performance improvement of around **10x** when comparing the `v0.9.5` and **8x** when comparing to `strawberry-django-plus`

## Changes

* refactor!: overall revamp of the type/field code and typing improvements by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/265
* feat: relay integration by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/267
* feat: ModelProperty descriptor by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/268
* feat: query optimizer extension by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/271
* feat: enum integration by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/270
* feat: improved mutations by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/272
* feat: permissions extensions using the django's permissioning system by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/273
* docs: document all new features from this lib and improve existing ones by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/274

0.9.5 - 2023-06-15
-------------------

## What's Changed
* add .DS_Store to gitignore by @capital-G in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/248
* Add kwargs to the documentation about get_queryset by @cdroege in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/250
* Update test matrix to include django 4.2 by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/253
* chore: migrate from flake8/isort to ruff by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/237
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/259
* add strawberry.relay tests, fix compatibility with relay, fix other issues by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/260

0.9.4 - 2023-04-03
-------------------

## What's changed

* refactor: replace Extension by SchemaExtension as required by strawberry 0.160.0+
* fix: do not add filters to non list fields (thanks @g-as for reporting this regression)

0.9.3 - 2023-04-02
-------------------

## What's Changed
* Update test django version from 4.2a1 to 4.2b1 by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/241
* feature: backporting django-debug-toolbar from strawberry-django-plus by @frleb in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/239
* refactor: do not insert `pk` arguments inside non root fields by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/246

0.9.2 - 2023-02-04
-------------------

## What's changed

* chore: do not limit django/strawberry upper bound versions

0.9.1 - 2023-02-03
-------------------

## What's Changed
* Add django 4.0,4.2 to tests & updated minor versions by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/228
* Fix private field handling by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/231

0.9 - 2023-01-14
-------------------

## What's Changed
* fix(typo): Fix typo in table of contents by @rennerocha in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/216
* removed `django-filter` from pyproject.toml, added tests matrix by @nrbnlulu in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/219
* Add actionlint for GitHub Actions files by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/221
* Fix django version matrix. by @nrbnlulu in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/222
* Geos fields query & mutation support by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/213
* Started docs for query by @ccsv in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/147

0.8.2 - 2022-11-16
-------------------

## What's Changed
* make pk argument required when querying single object by @stygmate in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/214

0.8.1 - 2022-11-10
-------------------

## What's Changed
* fix: Fix resolver annotation resolution by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/212

0.8 - 2022-11-06
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/203
* Change how we set the default annotation by @patrick91 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/206

0.7.1 - 2022-10-28
-------------------

## What's Changed
* fix: Prevent memory leaks when checking if the search method accepts an info keyword
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/198
* Updates documentation for `get_queryset` by @fireteam99 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/199
* Update pagination.md by @fabien-michel in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/202
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/201
0.7 - 2022-10-16
-------------------

## What's Changed
* Pass info for generic filter type by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/197

0.6 - 2022-10-11
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/192
* Implementing filter, order and pagination in `StrawberryDjangoField` super classes by @ManiacMaxo in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/193
* Allow passing info in filters by @kwongtn in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/191

0.5.4 - 2022-10-10
-------------------

## What's Changed
* import TypedDict from typing_extensions for Python 3.7 by @whardeman in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/189
* Fix demo app by @moritz89 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/190
* fix: get_queryset sends self in fields.py which it shouldnt by @deshk04 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/188

0.5.3 - 2022-10-01
-------------------

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/178
* Fix mutations and filtering for when using strawberry-graphql >=0.132.1 by @jkimbo in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/183
* Broaden is_strawberry_django_field to support custom field classes by @benhowes in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/185

0.5.2 - 2022-09-28
-------------------

## What's Changed
* Pin strawberry-graphql to <0.132.1 by @jkimbo in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/184

0.5.1 - 2022-09-12
-------------------

## What's changed

* [fix: Only append order to the resolver if it is a list](https://github.com/strawberry-graphql/strawberry-graphql-django/commit/5d85c4b43842cb401506c86954a33e94251e53c8)
0.5 - 2022-09-10
-------------------

## What's Changed
* Update docs link in README by @q0w in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/154
* Documentation for overriding the field class by @benhowes in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/158
* fix: Raise NotImplementedError on unknown Django fields by @noelleleigh in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/161
* Add many type hints by @noelleleigh in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/162
* adding installation with pip by @sisocobacho in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/166
* feat: Use Django textual metadata in GraphQL  by @noelleleigh in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/160
* Update pagination.md by @tanaydin in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/170
* Fix field ordering inheritance by @DanielHuisman in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/176
* fix(doc): update mkdocs.yml to point to correct branch by @DavidLemayian in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/175
0.4 - 2022-07-09
-------------------

## What's Changed
* Update docs language and formatting by @augustebaum in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/124
* feature: allow overriding field class by @benhowes in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/135
* Site for docs by @nrbnlulu in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/140
* feat: link JSONField to strawberry.scalars.JSON by @FlickerSoul in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/144
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/141

0.3.1 - 2022-06-29
-------------------

## What's Changed
* docs: document how to use a custom filter logic by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/116
* fixed various typos by @g-as in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/118
* Change order of inheritance for `StrawberryDjangoField` by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/122
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/123
* feat: allow Enums to work with FilterLookup by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/126
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/127
* fix: pass through more field attributes by @benhowes in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/129
* fix: resolve `ManyToManyRel` and `ManyToOneRel` as non-null lists by @FlickerSoul in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/131
0.3 - 2022-05-23
-------------------

## What's Changed
* Feature: Register mutation by @NeoLight1010 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/45
* Fix filtering in `get_queryset` of types with enabled pagination by @illia-v in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/60
* Add permissions to django mutations by @wellzenon in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/53
* Fix a bug related to creating users with unhashed passwords by @illia-v in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/62
* pre-commit config file and fixes by @la4de in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/68
* Clean deprecated API by @la4de in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/69
* updated the way event loop is detected in 'is_async' by @g-as in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/72
* Fix detecting `auto` annotations when postponed evaluation is used by @illia-v in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/73
* Updated docs by @ccsv in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/78
* Fix incompatibility with Strawberry >= 0.92.0 related to interfaces by @illia-v in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/76
* Fixed issue with generating order args by @jaydensmith in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/90
* Update .gitignore to the python standard by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/97
* feat: add Enum support to filtering by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/100
* build: update packages by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/94
* Caching Extensions using Django Cache by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/93
* docs: filled in some missing info in the docs by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/98
* Fix ordering with custom filters by @hiporox in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/108
* bugfix: ignore filters argument if it is an arbitary argument by @devkral in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/115
* Fixing Quick Start by @akkim2 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/114
* Fix #110 - Add **kwargs passthrough on CUD mutations, enables "description" annotation from Strawberry. by @JoeWHoward in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/111
* Use auto from strawberry instead of define our own by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/101
* Fix filtering cannot use relational reflection fields by @star2000 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/109
* refactor: Change the use of "is_unset" to "is UNSET" by @bellini666 in https://github.com/strawberry-graphql/strawberry-graphql-django/pull/117
