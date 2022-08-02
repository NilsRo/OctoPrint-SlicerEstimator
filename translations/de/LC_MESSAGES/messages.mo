��    &      L              |  ,   }  W   �  g        j  �   w  )         *  L   1     ~     �     �  E   �     �     �  �         �     �     �    �     �     �     �  x   �     s    z  Y   �     �     �  H   	  $   [	  ;   �	  �   �	  �   j
     S     \     s     x  �  ~  /   #  [   S  k   �       �   1  (   �     �  <   �     &     7     C  L   P     �     �  �   �  	   ^  	   h     r  -       �  	   �     �  �   �     v  �   }  \   ?     �  #   �  V   �  5     A   R  �   �  �   a     P     Y     p     u   (restart of GUI - Browsersession - required) Add custom metadata like filament brand, material,... in OctoPrints current print view. Add custom metadata like filament brand, material,... in OctoPrints filebrowser after uploading a file. Add metadata Additional support or a manual is available on <a href="https://github.com/NilsRo/OctoPrint-SlicerEstimator" target="_blank">Github</a>. Based on information added by the slicer. Bottom Change the orientation in the filelist above or below the standard metadata. Create issue Current print Description Developer settings - use at your own risk / enable it on request only Development Filelist How to add custom metadata to OctoPrints filelist see <a href="https://github.com/NilsRo/OctoPrint-SlicerEstimator" target="_blank">here</a>! Main Metadata Metadata ID Metadata has to be added in the Start GCODE in this format: (;Slicer info:&lt;key&gt;;&lt;value&gt;). You can add as much metadata as you like. You can find an
                    example <a href="https://github.com/NilsRo/Cura_Anycubic_MegaS_Profile" target="_blank">here</a> for Cura. Orientation Print time estimation Refresh Metadata Remaining time is read out of M73 commands added by PrusaSlicer. This will update continuously the remaining print time. Slicer The average estimation is based on the last prints (green dot is shown). It can be more accurate in the first minutes compared to the slicer estimation as it also includes the heatup time of the printer and is based on the print-history. After print-start slicer estimation is fine. The slicer is selected automatically. If this does not work anymore please open a Ticket. Top Update from development branch Use Refresh to update metadata from files. It will not delete entries... Use average estimation before slicer Use development branch <b>Restart of OctoPrint required</b> With Cura native no changes have to be applied to Cura. The overall print time is read out of a comment in the GCODE. This will update continuously the remaining print time. With Simplify3D no changes has to be applied to Simplify3D. The overall print time is read out of a comment in the GCODE. For a correct estimation OctoPrints percentage done is used as there is only the overall print time available. filament filament change (M600) tool up to Project-Id-Version: OctoPrint-SlicerEstimator 1.3.5
Report-Msgid-Bugs-To: i18n@octoprint.org
POT-Creation-Date: 2022-08-02 22:31+0200
PO-Revision-Date: 2022-05-05 19:16+0200
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language: de
Language-Team: de <LL@li.org>
Plural-Forms: nplurals=2; plural=(n != 1);
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Generated-By: Babel 2.10.3
 (Neustart der GUI - Browsersession - notwendig) Zeige eigene Metadaten wie Filamenthersteller, Material, ... in OctoPrints Druckbereich an. Ergänze eigene Metadaten wie Filamenthersteller, Material, ... in OctoPrints Dateibrowser nach dem Upload. Metadaten hinzufügen Support und eine Anleitung sind verfügbar auf <a href="https://github.com/NilsRo/OctoPrint-SlicerEstimator" target="_blank">Github</a>. basierend aus der Schätzung des Slicers unten Ändere die Ausrichtung im Dateibrowser auf oben oder unten. Ticket erstellen Druckstatus Beschreibung Entwickler-Einstellungen - auf eigene Gefahr / nur auf Rückfrage aktivieren Entwicklung Dateibrowser Wie man eigene Metadaten zu OctoPrints Dateibrowser hinzufügen kann findet man <a href="https://github.com/NilsRo/OctoPrint-SlicerEstimator" target="_blank">hier</a>! Allgemein Metadaten Metadaten ID Metadaten müssen im Start GCODE im folgenden Format ergänzt werden: (;Slicer info:&lt;key&gt;;&lt;value&gt;). Du kannst so viele Metadaten hinzufügen wie du magst. Du kannst ein Beispiel hier <a href="https://github.com/NilsRo/Cura_Anycubic_MegaS_Profile" target="_blank">hier</a> für Cura finden. Ausrichtung Druckzeit Metadaten aktualisieren Die Druckzeit wird aus den M73 Kommandos vom PrusaSlicer ermittelt. Dies aktualisiert kontinuierlich die Druckzeit und ermöglicht eine genaue Berechnung. Slicer Die 'durchschittliche Druckzeit' wird aus den letzten Drucken ermittelt (grüner Punkt). Dies ist meistens genauer als die vom Slicer ermittelte Zeit und berücksichtigt auch die Aufwärmphase. Der Slicer wird automatisch ausgewählt. Funktioniert dies nicht bitte ein Ticket eröffnen. oben Aktualisieren aus Entwickler-Branch Nutze 'Aktualisieren' um die Metadaten neu einzulesen. Dies löscht keine Einträge... Nutze die 'durchschittliche Druckzeit' wenn vorhanden Benutze Entwickler-Branch <b>Neustart von OctoPrint notwendig</b> Bei Cura müssen keine Änderungen am Slicer durchgeführt werden, da diese aus den GCODE Kommentaren gelesen werden. Dies aktualisiert kontinuierlich die Druckzeit und ermöglicht eine genaue Berechnung. Bei Simplify3D müssen keine Änderungen am Slicer durchgeführt werden, da diese aus den GCODE Kommentaren gelesen werden. Für die Berechnung während des Drucks wird auf die prozentuelle Druckfortschritt von OctoPrint zurückgegriffen. Filament Filamentwechsel (M600) Tool bis 