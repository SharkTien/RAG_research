import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.path import Path

# Create figure
fig, ax = plt.subplots(figsize=(16, 5.0), dpi=300)
ax.set_xlim(-0.2, 14.2)
ax.set_ylim(-1.3, 3.2)
ax.set_aspect('equal')
ax.axis('off')

# Colors matching the original image
box_edge_color = '#d8e2ee'
box_face_color = '#ffffff'
text_color = '#1f2937'
arrow_color = '#ff6a3d'
loop_text_color = '#ff6a3d'

box_width = 1.85
box_height = 0.85
corner_radius = 0.22

def draw_box(x, y, text):
    rect = FancyBboxPatch(
        (x - box_width/2, y - box_height/2),
        box_width, box_height,
        boxstyle=f"round,pad=0,rounding_size={corner_radius}",
        edgecolor=box_edge_color,
        facecolor=box_face_color,
        linewidth=1.4,
        zorder=3
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=11, 
            family='DejaVu Serif', color=text_color, linespacing=1.25, zorder=4)

def draw_arrow(x1, y1, x2, y2):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle='-|>,head_length=5,head_width=3',
        color=arrow_color,
        linewidth=1.5,
        shrinkA=1, shrinkB=2,
        zorder=2
    )
    ax.add_patch(arrow)

def draw_loop_below(x, y, label):
    # Loop curving below box
    x_start = x + 0.32
    x_end = x - 0.32
    y_box = y - box_height/2
    y_deep = y_box - 0.38
    
    verts = [
        (x_start, y_box),
        (x_start + 0.25, y_deep),
        (x_end - 0.25, y_deep),
        (x_end, y_box)
    ]
    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
    path = Path(verts, codes)
    
    arrow = FancyArrowPatch(
        path=path,
        arrowstyle='-|>,head_length=4.8,head_width=2.8',
        color=arrow_color,
        linewidth=1.4,
        shrinkA=0.5, shrinkB=1.5,
        zorder=2
    )
    ax.add_patch(arrow)
    ax.text(x, y_deep - 0.12, label, ha='center', va='top', fontsize=9.5,
            family='DejaVu Serif', color=loop_text_color, zorder=4)

# Positions
y_row1 = 2.35
y_row2 = 0.35

# Row 1 nodes
nodes_row1 = [
    (0.8, "Interview"),
    (3.2, "Checkpoint\ncandidate"),
    (5.6, "Checkpoint\napproved"),
    (8.0, "Type\nselected"),
    (10.4, "Question\ndraft"),
    (12.8, "QA\nconfirmed")
]

for x, label in nodes_row1:
    draw_box(x, y_row1, label)

# Draw horizontal arrows row 1
for i in range(len(nodes_row1) - 1):
    x_curr = nodes_row1[i][0] + box_width/2
    x_next = nodes_row1[i+1][0] - box_width/2
    draw_arrow(x_curr, y_row1, x_next, y_row1)

# Loops for row 1
draw_loop_below(3.2, y_row1, "reject / regenerate")
draw_loop_below(10.4, y_row1, "suggest another")

# Row 2 nodes
draw_box(12.8, y_row2, "Activity\ncreated")
draw_box(10.4, y_row2, "Editor\nreview")

# Vertical arrow from QA confirmed to Activity created
draw_arrow(12.8, y_row1 - box_height/2, 12.8, y_row2 + box_height/2)

# Horizontal arrow from Activity created to Editor review
draw_arrow(12.8 - box_width/2, y_row2, 10.4 + box_width/2, y_row2)

# Loop for Editor review
draw_loop_below(10.4, y_row2, "edit / save")

plt.tight_layout()
output_path = "d:/Datastore/ntc/mini_RAG/pipeline_diagram.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print("Successfully generated diagram at", output_path)
