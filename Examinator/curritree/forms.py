from django import forms
from .models import TreeNode  # Assuming TreeNode is in the same directory or you adjust the import

class NodeForm(forms.ModelForm):
    CHILD_TYPE_MAP = {
        'board': ['class', 'subject'], # Added 'subject' for flexibility
        'competitive': ['subject'],
        'class': ['subject'],
        'subject': ['chapter'],
        'chapter': ['unit'],
        'unit': ['section'],
    }

    class Meta:
        model = TreeNode
        fields = ['name', 'node_type', 'parent', 'order', 'metadata']
        widgets = {
            'metadata': forms.Textarea(attrs={'rows': 3, 'placeholder': '{"key": "value"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        is_creating = not self.instance or not self.instance.pk
        
        # --- Data Retrieval ---
        parent_id = self.initial.get("parent") or self.data.get("parent")
        current_node_type = self.instance.node_type if self.instance.pk else None
        posted_node_type = self.data.get("node_type")
        
        # The type we must ensure is present in choices to pass validation
        type_to_validate = posted_node_type or current_node_type
        
        # Start with all type choices available for filtering
        valid_type_choices = list(self.fields["node_type"].choices)


        # ====================================================================
        # === 1. EDITING MODE LOGIC (Instance exists) ===
        # ====================================================================
        if not is_creating:
            current_node = self.instance
            current_type = current_node.node_type

            # A. Node Type Handling: Lock the field for editing
            # The node type is determined by its parent and should not change.
            self.fields['node_type'].disabled = True
            
            # For a disabled field, ensure the choices only contain the current valid value
            # to prevent validation errors if Django still checks it.
            self.fields["node_type"].choices = [
                (current_type, current_node.get_node_type_display()),
            ]
            self.fields["node_type"].initial = current_type

            # B. Parent Field Filtering: Exclude self and descendants
            queryset = TreeNode.objects.exclude(pk=current_node.pk)
            descendants_pks = [d.pk for d in current_node.get_descendants(include_self=False)]
            queryset = queryset.exclude(pk__in=descendants_pks)
            
            # Restrict parent queryset based on the current/posted node type
            type_for_parent_filter = posted_node_type or current_type
            
            if type_for_parent_filter:
                allowed_parent_types = [
                    k for k, v in self.CHILD_TYPE_MAP.items()
                    if type_for_parent_filter in v
                ]
                
                # Further restrict the queryset based on allowed parent types
                queryset = queryset.filter(node_type__in=allowed_parent_types)

            self.fields["parent"].queryset = queryset
            
            # Ensure current parent is still available
            if current_node.parent and current_node.parent not in self.fields["parent"].queryset:
                self.fields["parent"].queryset = (
                    self.fields["parent"].queryset | TreeNode.objects.filter(pk=current_node.parent.pk)
                )

            # If the current node is a root node, parent must be null
            if current_node.is_root():
                self.fields["parent"].required = False
                self.fields["parent"].queryset = TreeNode.objects.none()

        # ====================================================================
        # === 2. CREATION MODE LOGIC (No instance) ===
        # ====================================================================
        else:
            if parent_id:
                # A. Node Type Filtering based on PARENT
                try:
                    parent_node = TreeNode.objects.get(pk=parent_id)
                    
                    # Ensure the parent field itself is available in the queryset for validation
                    # Note: We do *not* over-filter the parent queryset here, allowing default validation.
                    
                    allowed_types = self.CHILD_TYPE_MAP.get(parent_node.node_type, [])
                    
                    # FIX: Always include the submitted type for failed validation
                    if type_to_validate and type_to_validate not in allowed_types:
                        allowed_types.append(type_to_validate)
                    
                    self.fields["node_type"].choices = [
                        (val, label) for val, label in valid_type_choices
                        if val in allowed_types
                    ]
                    
                except TreeNode.DoesNotExist:
                    # If parent_id is invalid, let the parent field validation handle the error.
                    pass 
                
            else:
                # B. Root Node Creation
                self.fields["parent"].queryset = TreeNode.objects.none()
                self.fields["parent"].required = False
                
                allowed_types = ["board", "competitive"]
                
                # FIX: Always include the submitted type for failed validation
                if type_to_validate and type_to_validate not in allowed_types:
                    allowed_types.append(type_to_validate)

                self.fields["node_type"].choices = [
                    (val, label) for val, label in valid_type_choices
                    if val in allowed_types
                ]


    def clean_metadata(self):
        metadata = self.cleaned_data.get('metadata')
        if metadata:
            try:
                import json
                json.loads(metadata)
            except ValueError:
                raise forms.ValidationError("Metadata must be valid JSON.")
        return metadata