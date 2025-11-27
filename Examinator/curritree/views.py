# hierarchy/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import TreeNode
from .forms import NodeForm
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError, transaction
import json
from django.contrib.auth.decorators import permission_required
from accounts.views import staff_required, superuser_required
from django.contrib.auth.decorators import login_required

@login_required
@staff_required
@permission_required('curritree.view_treenode',login_url='profile_update')
def index(request):
    # Fetch all root nodes
    all_roots = TreeNode.objects.filter(parent__isnull=True).order_by('order', 'name')
    
    # Separate them based on node_type
    boards = all_roots.filter(node_type='board')
    competitive_exams = all_roots.filter(node_type='competitive')
    
    context = {
        'boards': boards,
        'competitive_exams': competitive_exams,
    }
    return render(request, 'hierarchy/curriculum_list.html', context)

@login_required
@staff_required
@permission_required('curritree.view_treenode',login_url='profile_update')
def detail(request, pk):
    node = get_object_or_404(TreeNode, pk=pk)
    children = node.children.all().order_by('order', 'name')

    # Build breadcrumb
    breadcrumb = []
    current = node
    while current:
        breadcrumb.append(current)
        current = current.parent
    breadcrumb.reverse()

    return render(request, 'hierarchy/curriculum_detail.html', {
        'node': node,
        'children': children,
        'breadcrumb': breadcrumb,
    })


# These choices must match the options in the TreeNode model
NODE_TYPE_CHOICES = [
    ('board', 'Board/University'),
    ('competitive', 'Competitive Exam'),
    ('class', 'Class/Level'),
    ('subject', 'Subject'),
    ('chapter', 'Chapter'),
    ('unit', 'Unit'),
    ('section', 'Section'),
]

# This map defines which node types can be children of which parent types
CHILD_TYPE_MAP = {
    'board': ['class', 'subject'],
    'competitive': ['subject'],
    'class': ['subject'],
    'subject': ['chapter','unit'],
    'unit': ['chapter'],
    'chapter': ['section'],
    # 'section' has no allowed children, thus not in the map
}
# --------------------------------------------------------------------------


def _validate_and_save_node(data, instance=None):
    """
    Manually validates and saves TreeNode data, returning (node, errors).
    
    Returns:
        tuple: (saved_node_instance, errors_dict)
    """
    errors = {}
    
    # 1. Name Validation
    name = data.get('name', '').strip()
    if not name:
        errors['name'] = 'Name is required.'
    
    # 2. Order Validation
    order_str = data.get('order', None)
    try:
        order = int(order_str) if order_str else None
        if order is None:
             errors['order'] = 'Order is required.'
        elif order < 0:
            errors['order'] = 'Order must be a non-negative number.'
    except ValueError:
        errors['order'] = 'Order must be a valid integer.'
        order = None # Reset to None if invalid
        
    # 3. Metadata Validation
    metadata_raw = data.get('metadata', '').strip()
    metadata = {}
    if metadata_raw:
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            errors['metadata'] = 'Metadata must be valid JSON format (e.g., {"key": "value"}).'

    # 4. Parent Validation
    parent_pk_str = data.get('parent')
    parent_node = None
    if parent_pk_str:
        try:
            parent_node = TreeNode.objects.get(pk=parent_pk_str)
        except TreeNode.DoesNotExist:
            errors['parent'] = 'Invalid parent node selected.'
    
    # 5. Node Type Validation (Crucial for hierarchy)
    node_type = data.get('node_type', None)
    
    if not node_type or node_type not in [c[0] for c in NODE_TYPE_CHOICES]:
        errors['node_type'] = 'Invalid node type selected.'
    
    # 6. Marks Check
    marks_str = data.get('marks', None)
    try:
        marks = int(marks_str) if marks_str else 0
        if marks < 0:
            errors['marks'] = 'Marks must be a non-negative number.'
    except ValueError:
        errors['marks'] = 'Marks must be a valid integer.'
        marks = 0 # Reset to 0 if invalid 
    
    # Hierarchy Check
    if parent_node and node_type:
        allowed_children = CHILD_TYPE_MAP.get(parent_node.node_type, [])
        if node_type not in allowed_children:
            errors['node_type'] = f"A '{parent_node.node_type}' node cannot have a '{node_type}' child."
    elif not parent_node and node_type and node_type not in ['board', 'competitive']:
        # Root nodes must be 'board' or 'competitive'
        errors['node_type'] = f"A root node must be 'Board/University' or 'Competitive Exam', not '{node_type}'."

    # If editing, prevent reparenting to self or descendants (simplified check)
    if instance and parent_node and parent_node.pk == instance.pk:
         errors['parent'] = "A node cannot be its own parent."

    # --- SAVE LOGIC ---
    if not errors:
        try:
            with transaction.atomic():
                if instance:
                    # Editing existing node
                    instance.name = name
                    instance.node_type = node_type # Note: Type change is restricted by validation logic above
                    instance.parent = parent_node
                    instance.order = order
                    instance.metadata = metadata
                    if marks is not None:
                        instance.marks = marks
                    instance.save()
                    return (instance, {})
                else:
                    # Creating new node
                    node_kwargs = dict(
                        name=name,
                        node_type=node_type,
                        parent=parent_node,
                        order=order,
                        metadata=metadata,
                    )

                    if marks is not None:
                        node_kwargs["marks"] = marks

                    node = TreeNode.objects.create(**node_kwargs)

                    return (node, {})
        except IntegrityError as e:
            errors['general'] = f"A database error occurred: {e}"
            return (None, errors)
    
    return (None, errors)


# ========================================================================
# 1. CREATE ROOT NODE VIEW
# ========================================================================

@require_http_methods(["GET", "POST"])
@login_required
@staff_required
@permission_required('curritree.add_treenode',login_url='profile_update')
def create_node(request):
    """View to create a new root node."""
    initial_data = {}
    errors = {}
    
    if request.method == 'POST':
        # Data from POST request
        initial_data = request.POST.dict()
        
        # Manually set parent to empty string for validation as a root node
        initial_data['parent'] = '' 
        
        node, errors = _validate_and_save_node(initial_data)
        
        if node:
            return redirect('curritree:curriculum_detail', pk=node.pk)
    
    context = {
        'is_editing': False,
        'initial_data': initial_data,
        'errors': errors,
        'node_type_choices': NODE_TYPE_CHOICES, # Full list for root node selector
        # parent_node is None for root creation
    }
    return render(request, 'hierarchy/curriculum_form.html', context)


# ========================================================================
# 2. CREATE CHILD NODE VIEW
# ========================================================================

@require_http_methods(["GET", "POST"])
@login_required
@staff_required
@permission_required('curritree.add_treenode',login_url='profile_update')
def create_child_node(request, parent_pk):
    """View to create a new child node under a given parent."""
    
    parent_node = get_object_or_404(TreeNode, pk=parent_pk)
    
    # Pre-populate initial data with fixed parent and implied child node type
    parent_type = parent_node.node_type
    allowed_child_types = CHILD_TYPE_MAP.get(parent_type, [])

    print("Allowed child types:", allowed_child_types)  # Debugging line
    
    # Default to the first allowed child type for convenience
    initial_data = {
        'parent': str(parent_node.pk),
        'node_type': allowed_child_types[0] if allowed_child_types else '',
    }
    errors = {}
    
    if request.method == 'POST':
        # Get data, ensuring the parent is fixed from the URL/initial data, 
        # even if tampered in the hidden field.
        post_data = request.POST.dict()
        post_data['parent'] = str(parent_node.pk) 
        initial_data.update(post_data) # Use POST data to populate fields on error
        
        node, errors = _validate_and_save_node(post_data)
        
        if node:
            return redirect('curritree:curriculum_detail', pk=node.pk)
            
    context = {
        'is_editing': False,
        'parent_node': parent_node,  # Used by template for read-only parent display
        'initial_data': initial_data,
        'errors': errors,
        'node_type_choices': NODE_TYPE_CHOICES if parent_type != 'subject' else [(ct, dict(NODE_TYPE_CHOICES)[ct]) for ct in allowed_child_types]   ,
    }
    return render(request, 'hierarchy/curriculum_form.html', context)


# ========================================================================
# 3. EDIT NODE VIEW
# ========================================================================

@require_http_methods(["GET", "POST"])
@login_required
@staff_required
@permission_required('curritree.change_treenode',login_url='profile_update')
def edit_node(request, pk):
    """View to edit an existing node."""
    
    node = get_object_or_404(TreeNode, pk=pk)
    
    # Initial data from the existing instance
    initial_data = {
        'name': node.name,
        'node_type': node.node_type,
        'parent': str(node.parent.pk) if node.parent else '',
        'order': node.order,
        'marks': node.marks,
        'metadata': json.dumps(node.metadata) if node.metadata else '',
    }
    errors = {}
    
    if request.method == 'POST':
        post_data = request.POST.dict()
        # Ensure that if the parent field is read-only (which it is in the template) 
        # the correct parent ID is used from the POST or initial data.
        if 'parent' not in post_data and node.parent:
            post_data['parent'] = str(node.parent.pk)
            
        initial_data.update(post_data) # Update initial data with posted values on error
        
        node, errors = _validate_and_save_node(post_data, instance=node)
        
        if node:
            return redirect('curritree:curriculum_detail', pk=node.pk)
    
    context = {
        'is_editing': True,
        'node': node,
        'initial_data': initial_data,
        'errors': errors,
        'node_type_choices': NODE_TYPE_CHOICES,
    }
    return render(request, 'hierarchy/curriculum_form.html', context)

@login_required
def api_tree(request, root_id=None):
    depth = int(request.GET.get("depth", 3))  # default 3 levels
    def serialize(node, level=0):
        data = node.to_dict()
        if level < depth:
            data["children"] = [serialize(c, level+1) for c in node.children.all().order_by('order','name')]
        else:
            data["children"] = []
        return data

    if root_id:
        root = get_object_or_404(TreeNode, pk=root_id)
        return JsonResponse(serialize(root))
    else:
        roots = TreeNode.objects.filter(parent__isnull=True).order_by('order','name')
        return JsonResponse([serialize(r) for r in roots], safe=False)

@login_required
@staff_required
@permission_required('curritree.delete_treenode',login_url='profile_update')
def delete_node(request, pk):
    node = get_object_or_404(TreeNode, pk=pk)
    parent = node.parent
    if request.method == 'POST':
        node.delete()
        if parent:
            return redirect('curritree:curriculum_detail', pk=parent.pk)
        return redirect('curritree:curriculum_list')
    return render(request, 'hierarchy/curriculum_confirm_delete.html', {'node': node})


def get_ancestor_nodes(request, node_id):
    try:
        node = TreeNode.objects.get(pk=node_id)
        ancestors = node.get_ancestors(include_self=True)

        # if not request.user.is_superuser:
        #     # Ensure the user is logged in and has a profile
        #     if not request.user.is_authenticated:
        #          # For security, return an empty list or unauthorized error if access is required
        #         return JsonResponse({"error": "Authentication required"}, status=403)

        #     # Get the PKs of all nodes accessible via the user's M2M field
        #     accessible_node_pks = request.user.profile.academic_stream.values_list('pk', flat=True)
            
        #     # Filter the ancestors queryset to only include those whose PK 
        #     # is in the list of accessible nodes.
        #     ancestors = ancestors.filter(pk__in=accessible_node_pks)
        data = [{"id": n.id, "name": n.name, "node_type": n.node_type} for n in ancestors]
        return JsonResponse({"ancestors": data}, status=200)
    except TreeNode.DoesNotExist:
        return JsonResponse({"error": "Node not found"}, status=404)
    except Exception as e:
        print(f"An unexpected error occurred in get_ancestors: {e}")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)
    

def get_descendant_nodes(request, node_id):
    try:
        node = TreeNode.objects.get(pk=node_id)
        descendants = node.get_descendants(include_self=True)

        # if not request.user.is_superuser:
        #     # Ensure the user is logged in and has a profile
        #     if not request.user.is_authenticated:
        #          # For security, return an empty list or unauthorized error if access is required
        #         return JsonResponse({"error": "Authentication required"}, status=403)

        #     # Get the PKs of all nodes accessible via the user's M2M field
        #     accessible_node_pks = request.user.profile.academic_stream.values_list('pk', flat=True)
            
        #     # Filter the ancestors queryset to only include those whose PK 
        #     # is in the list of accessible nodes.
        #     descendants = descendants.filter(pk__in=accessible_node_pks)
        data = [{"id": n.id, "name": n.name, "node_type": n.node_type} for n in descendants]
        return JsonResponse({"children": data}, status=200)
    except TreeNode.DoesNotExist:
        return JsonResponse({"error": "Node not found"}, status=404)
    except Exception as e:
        print(f"An unexpected error occurred in get_ancestors: {e}")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)