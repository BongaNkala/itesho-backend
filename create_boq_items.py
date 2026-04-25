from core.models import Project, BOQItem
from django.contrib.auth.models import User

# Get project
project = Project.objects.first()
if not project:
    print("No project found. Create one first.")
else:
    print(f"Project: {project.name} (ID: {project.id})")
    
    # Check existing items
    items = BOQItem.objects.filter(project=project, level=3)
    print(f"Existing level 3 items: {items.count()}")
    
    if items.count() == 0:
        # Create section
        section = BOQItem.objects.create(
            project=project,
            item_code='01',
            description='Earthworks',
            unit='lump_sum',
            planned_quantity=1,
            rate=0,
            level=1
        )
        print(f"Created section: {section.id}")
        
        # Create subsection
        subsection = BOQItem.objects.create(
            project=project,
            parent=section,
            item_code='01.01',
            description='Excavation',
            unit='lump_sum',
            planned_quantity=1,
            rate=0,
            level=2
        )
        print(f"Created subsection: {subsection.id}")
        
        # Create line item 1
        line_item = BOQItem.objects.create(
            project=project,
            parent=subsection,
            item_code='01.01.01',
            description='Bulk Excavation',
            unit='m³',
            planned_quantity=500,
            rate=150,
            level=3
        )
        print(f"Created line item: {line_item.id} - {line_item.description} (Planned: 500 m³ @ R150)")
        
        # Create line item 2
        line_item2 = BOQItem.objects.create(
            project=project,
            parent=subsection,
            item_code='01.01.02',
            description='Trench Excavation',
            unit='m³',
            planned_quantity=200,
            rate=120,
            level=3
        )
        print(f"Created line item: {line_item2.id} - {line_item2.description} (Planned: 200 m³ @ R120)")
        
        print("\n✓ BOQ items created successfully!")
    else:
        print("BOQ items already exist:")
        for item in items:
            print(f"  - {item.item_code}: {item.description}")
    
    # Verify final items
    final_items = BOQItem.objects.filter(project=project, level=3)
    print(f"\n✓ Total level 3 items now: {final_items.count()}")
    for item in final_items:
        print(f"  - {item.item_code}: {item.description} ({item.unit}) - Planned: {item.planned_quantity} @ R{item.rate}")
