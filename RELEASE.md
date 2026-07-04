Release type: patch

Resolve prefetch-optimized nested connections on the event loop instead of
paying a `sync_to_async` thread hop per parent node: the nested-connection
default resolver, the queryset hook for prefetch-optimized querysets and
`totalCount` served from the prefetched window annotation no longer touch
the database, so they no longer need a worker thread.
