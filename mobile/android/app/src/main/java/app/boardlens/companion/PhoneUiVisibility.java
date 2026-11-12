package app.boardlens.companion;
import java.util.*;
/** Count started app screens, so transitions/rotation never expose our own preview. */
final class PhoneUiVisibility {
 private static final Set<Object> screens=Collections.newSetFromMap(new IdentityHashMap<>());
 static synchronized void start(Object screen){screens.add(screen);ScreenService.setPhoneVisible(true);}
 static synchronized void stop(Object screen){screens.remove(screen);ScreenService.setPhoneVisible(!screens.isEmpty());}
}
