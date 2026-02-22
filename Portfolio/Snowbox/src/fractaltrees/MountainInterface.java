/**
 *
 * File: MountainInterface.java
 *
 * Author: Nikola Georgeiv
 *
 * Date: 11/28/2023
 */
package fractaltrees;

import java.awt.Graphics2D;

public interface MountainInterface {
    public void buildMountain(int level, double x0, double y0, double x1, double y1, Graphics2D g2d);
    public void drawMountain(int x, int y, Graphics2D g2d);
    public void saveMountain();
    public void displayMountain();
}
