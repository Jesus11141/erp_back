from django.db import models

class KnowledgeArticle(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    question = models.TextField()
    solution = models.TextField()
    useful_votes = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-useful_votes', '-created_at']

    def __str__(self):
        return f"KB #{self.id} (Tenant {self.tenant_id})"
