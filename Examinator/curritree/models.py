
from django.contrib.postgres.fields import JSONField
from accounts.models import TimeStampedModel
from django.db import models

class TreeNode(TimeStampedModel):
    name = models.CharField(max_length=100)
    NODE_TYPES = (
        ('board', 'Board'),
        ('competitive', 'Competitive Exam (JEE/CET)'),
        ('class', 'Class/Grade'),
        ('subject', 'Subject'),
        ('unit', 'Unit/Module'),
        ('chapter', 'Chapter/Topic'),
        ('section', 'Section'), # Added the section type
    )
    
    
    # 🛑 CRITICAL CHANGE: Use choices for the node_type field
    node_type = models.CharField(
        max_length=64, 
        choices=NODE_TYPES, # Use the defined choices
        help_text="Type of node, e.g. board, class, subject, chapter, unit, section"
    )
    
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    order = models.IntegerField(default=0, help_text="Order of the node among its siblings")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata for the node")
    marks = models.IntegerField(default=0, help_text="Marks allocated to this node")

    class Meta:
        ordering = ['parent_id','order','name']
        unique_together = ('parent', 'name', 'node_type')
    
    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"
    
    def get_ancestors(self, include_self=False):
        """
        Returns ancestors ordered from root -> parent.
        Note: This is O(depth) and does queries per step; OK for moderate depth.
        """
        node = self if include_self else self.parent
        ancestors = []
        while node:
            ancestors.insert(0, node)
            node = node.parent
        return ancestors
    
    def get_path_display(self, sep=' > '):
        return sep.join([f"{n.name}" for n in self.get_ancestors(include_self=True)])
    
    def get_descendants(self, include_self=False):
        """
        Returns all descendants in a flat list.
        """
        descendants = []
        if include_self:
            descendants.append(self)
        for child in self.children.all():
            descendants.extend(child.get_descendants(include_self=True))
        return descendants
    
    def get_siblings(self, include_self=False):
        """
        Returns all siblings ordered by 'order'.
        If include_self=True, includes the current node as well.
        """
        if self.parent:
            qs = self.parent.children.order_by("order")
            return qs if include_self else qs.exclude(id=self.id)
        else:
            # Root nodes (siblings are other roots)
            qs = TreeNode.objects.filter(parent__isnull=True).order_by("order")
            return qs if include_self else qs.exclude(id=self.id)
        
    def is_descendant_of(self, node):
        """Check if this node is a descendant of the given node."""
        ancestor = self.parent
        while ancestor:
            if ancestor == node:
                return True
            ancestor = ancestor.parent
        return False
    
    def _reorder_siblings(self):
        """Ensure siblings are ordered correctly by 'order' field."""
        siblings = self.get_siblings(include_self=True).order_by("order", "id")
        for idx, sib in enumerate(siblings):
            if sib.order != idx:
                sib.order = idx
                sib.save(update_fields=["order"])

    
    def is_root(self):
        return self.parent is None
    
    def move_to(self, new_parent, new_order=None):
        """
        Move this node to a new parent and optionally a new order.
        """
        if new_parent == self or (new_parent and new_parent.is_descendant_of(self)):
            raise ValueError("Cannot move a node to itself or its descendant.")
        
        self.parent = new_parent
        if new_order is not None:
            self.order = new_order
        self.save()
        self._reorder_siblings()

    def to_dict(self,depth=None):
        """
        Convert the node and its children to a dictionary representation.
        """
        data = {
            'id': self.id,
            'name': self.name,
            'node_type': self.node_type,
            'metadata': self.metadata,
            'children': []
        }
        if depth is None or depth > 0:
            for child in self.children.all():
                data['children'].append(child.to_dict(None if depth is None else depth-1))
        return data
    
    def get_next_sibling(self):
        return self.get_siblings().filter(order__gt=self.order).first()

    def get_previous_sibling(self):
        return self.get_siblings().filter(order__lt=self.order).last()

    def get_root(self):
        node = self
        while node.parent:
            node = node.parent
        return node