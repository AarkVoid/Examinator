def get_licensed_node_ids(org):
    """
    Returns all TreeNode IDs the organization is licensed for,
    including descendants.
    """
    ids = set()
    for grant in org.license_grants.all():
        for node in grant.curriculum_node.all():
            for n in node.get_descendants(include_self=True):
                ids.add(n.id)
    return ids