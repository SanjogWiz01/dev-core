#include <graphics.h>

int main() {
    int gd = DETECT, gm;
    initgraph(&gd, &gm, "");
    circle(100, 100, 50);
    getch();
    closegraph();
    return 0;
}

