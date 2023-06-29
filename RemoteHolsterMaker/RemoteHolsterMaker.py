#Author-
#Description-

import math
import adsk.core, adsk.fusion, adsk.cam, traceback

#############################################
# Globals
#############################################
_app = adsk.core.Application.cast(None)
_ui = adsk.core.UserInterface.cast(None)
_des = adsk.fusion.Design.cast(None)
_handlers = []
_commandId = 'Remote Holster Maker'

#############################################
# Default Values
#############################################

defaultHolsterName = "TV Remote Holster"

# Remote Details
#
defaultRemoteWidth = 80.0
defaultRemoteLength = 44.0
defaultRemoteThickness = 15.0

# Holster Details
#
defaultFrontSlotWidth = 10.0
defaultFrontHeight = 22.0

# Holster Appearance
#
defaultBackCornerRound = 4.0
defaultSoftenFillet = 0.5
defaultFrontSlotRound = 3.0

# Holster Strength
#
defaultSideThickness = 3.0
defaultBackThickness = 3.0
defaultBottomThickness = 3.0

# Tolerance
#
defaultTolerance = 0.5

#############################################
# Global Command inputs
#############################################

_holsterName       = adsk.core.StringValueCommandInput.cast(None)
_remoteWidth       = adsk.core.FloatSpinnerCommandInput.cast(None)
_remoteLength      = adsk.core.FloatSpinnerCommandInput.cast(None)
_remoteThickness   = adsk.core.FloatSpinnerCommandInput.cast(None)
_frontSlotWidth    = adsk.core.IntegerSliderCommandInput.cast(None)
_frontHeight       = adsk.core.IntegerSliderCommandInput.cast(None)
_backCornerRound   = adsk.core.IntegerSliderCommandInput.cast(None)
_softenFillet      = adsk.core.FloatSpinnerCommandInput.cast(None)
_frontSlotRound    = adsk.core.IntegerSliderCommandInput.cast(None)
_sideThickness     = adsk.core.FloatSpinnerCommandInput.cast(None)
_backThickness     = adsk.core.FloatSpinnerCommandInput.cast(None)
_bottomThickness   = adsk.core.FloatSpinnerCommandInput.cast(None)
_tolerance         = adsk.core.IntegerSliderCommandInput.cast(None)

#############################################
# Global Command Groups
#############################################

_remoteDetailsGroup      = adsk.core.GroupCommandInput.cast(None)
_holsterDetailsGroup     = adsk.core.GroupCommandInput.cast(None)
_holsterAppearanceGroup  = adsk.core.GroupCommandInput.cast(None)
_holsterStrengthGroup    = adsk.core.GroupCommandInput.cast(None)
_toleranceGroup          = adsk.core.GroupCommandInput.cast(None)


#############################################
# Constants
#############################################
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
NEW_BODY = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
SCALE = 0.1

#############################################
# Utility Functions
#############################################
def createComponent(design: adsk.fusion.Design, name: str) -> adsk.fusion.Component:
    rootComp = design.rootComponent
    allOccs = rootComp.occurrences
    newOcc = allOccs.addNewComponent(adsk.core.Matrix3D.create())
    comp = newOcc.component
    comp.name = name
    return comp

def createPoint(x: float, y: float, z: float) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x, y, z)

def create2DPoint(x, y):
    return createPoint(x, y, 0)

def createDistance(d) -> adsk.core.ValueInput:
    return adsk.core.ValueInput.createByReal(d)

def createReal(r) -> adsk.core.ValueInput:
    return adsk.core.ValueInput.createByReal(r)

def close(a, b):
    return abs(a - b) < 1e-5 * SCALE

def createBaseRectSketch(component: adsk.fusion.Component) -> adsk.fusion.Profile:
    base_sketch = component.sketches.add(component.xYConstructionPlane)
    base_sketch.name = "Base Sketch"
    p0 = create2DPoint(0, 0)
    p1 = create2DPoint((_remoteWidth + 2 * _sideThickness) * SCALE, (_remoteThickness + _sideThickness + _backThickness) * SCALE)
    base_sketch.sketchCurves.sketchLines.addTwoPointRectangle(p0, p1)
    # FIXME: there must be a better way!
    base_rect_profile = base_sketch.profiles.item(0)
    return base_rect_profile

def createScrewHolesSketch(component: adsk.fusion.Component, diameter) -> adsk.core.ObjectCollection:
    sketch: adsk.fusion.Sketch = component.sketches.add(component.xZConstructionPlane)
    sketch.name = "Screw Holes Sketch"

    holesCenter = (_sideThickness + _remoteWidth / 2)
    holesBack = (_sideThickness + _remoteThickness)
    holesSpace = (_bottomThickness + _remoteLength) / 4 * -1
    
    sketch.sketchCurves.sketchCircles.addByCenterRadius(createPoint(holesCenter * SCALE, holesSpace * SCALE, holesBack * SCALE), diameter * SCALE)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(createPoint(holesCenter * SCALE, 3 * holesSpace * SCALE, holesBack * SCALE), diameter * SCALE)

    circles = adsk.core.ObjectCollection.create()
    for n in range(2):
        circles.add(sketch.profiles.item(n))

    return circles

def createPocketSketch(component: adsk.fusion.Component) -> adsk.core.ObjectCollection:
    sketch: adsk.fusion.Sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = "Pocket Sketch"
    
    p1 = createPoint((_sideThickness) * SCALE, (_sideThickness) * SCALE, (_remoteLength + _bottomThickness) * SCALE)
    p2 = createPoint((_sideThickness + _remoteWidth) * SCALE, (_sideThickness + _remoteThickness) * SCALE, (_remoteLength + _bottomThickness) * SCALE)

    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)

    rect = adsk.core.ObjectCollection.create()
    rect.add(sketch.profiles.item(0))

    return rect
            
def createFrontSketch(component: adsk.fusion.Component) -> adsk.core.ObjectCollection:
    sketch: adsk.fusion.Sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = "Front Sketch"

    p1 = createPoint(0, 0, (_remoteLength + _bottomThickness) * SCALE)
    p2 = createPoint((2 * _sideThickness + _remoteWidth) * SCALE, (_sideThickness + _remoteThickness) * SCALE, (_remoteLength + _bottomThickness) * SCALE)

    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)

    rect = adsk.core.ObjectCollection.create()
    rect.add(sketch.profiles.item(0))

    return rect

def createSlotSketch(component: adsk.fusion.Component) -> adsk.core.ObjectCollection:
    sketch: adsk.fusion.Sketch = component.sketches.add(component.xZConstructionPlane)
    sketch.name = "Slot Sketch"
    
    slotLeft = (2 * _sideThickness + _remoteWidth - _frontSlotWidth) / 2
    p1 = createPoint(slotLeft * SCALE, 0, 0)
    p2 = createPoint((slotLeft + _frontSlotWidth) * SCALE, -1 * (_frontHeight + _bottomThickness) * SCALE, 0)

    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
   
    rect = adsk.core.ObjectCollection.create()
    rect.add(sketch.profiles.item(0))

    return rect


def run(context):
    try:
        global _app, _ui, _des

        _app = adsk.core.Application.get()
        _ui  = _app.userInterface        
        doc = _app.activeDocument
        prods = doc.products
        _des = prods.itemByProductType('DesignProductType')
        if not _des:
            raise Exception('Failed to get fusion design.')

        activeProd = _app.activeProduct

        cmdDef = _ui.commandDefinitions.itemById(_commandId)
        if not cmdDef:
            # Create a command definition.
            cmdDef = _ui.commandDefinitions.addButtonDefinition(_commandId, 'Remote Holster Maker', 'Remote Holster Maker') 
        
        # Connect to the command created event.
        onCommandCreated = HolsterCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        
        # Execute the command.
        cmdDef.execute()

        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



#############################################
# Handlers
#############################################
class HolsterCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False
            onExecute = HolsterCommandExecuteHandler()
            cmd.execute.add(onExecute)
            onExecutePreview = HolsterCommandExecuteHandler()
            cmd.executePreview.add(onExecutePreview)
            onDestroy = HolsterCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            
            # keep the handler referenced beyond this function
            #
            _handlers.append(onExecute)
            _handlers.append(onExecutePreview)
            _handlers.append(onDestroy)

            finestIncrement = 1.0

            #define the inputs
            inputs = cmd.commandInputs
            
            global _holsterName
            global _remoteWidth, _remoteLength, _remoteThickness
            global _frontSlotWidth, _frontHeight
            global _backCornerRound, _softenFillet, _frontSlotRound
            global _sideThickness, _backThickness, _bottomThickness
            global _tolerance         
            global _remoteDetailsGroup, _holsterDetailsGroup, _holsterAppearanceGroup, _holsterStrengthGroup, _toleranceGroup 
            
            _holsterName = inputs.addStringValueInput(_commandId + '_holsterName', 'Holster Name', defaultHolsterName)
            
            # Remote details
            #
            _remoteDetailsGroup = inputs.addGroupCommandInput(_commandId + '_remoteDetailsGroup', 'Remote Details')
            _remoteDetailsGroup.isExpanded = True

            _remoteDetailsGroup.children.addFloatSpinnerCommandInput('remoteWidth', 'Remote Width', '', 0.25, 100.0, finestIncrement, defaultRemoteWidth)
            _remoteDetailsGroup.children.addFloatSpinnerCommandInput('remoteLength', 'Remote Length', '', 0.25, 100.0, finestIncrement, defaultRemoteLength)
            _remoteDetailsGroup.children.addFloatSpinnerCommandInput('remoteThickness', 'Remote Thickness', '', 0.25, 100.0, finestIncrement, defaultRemoteThickness)
            
            # Holster Details
            #            
            _holsterDetailsGroup = inputs.addGroupCommandInput(_commandId + '_holsterDetailsGroup', 'Holster Details')
            _holsterDetailsGroup.isExpanded = True

            _holsterDetailsGroup.children.addFloatSpinnerCommandInput('frontSlotWidth', 'Slot Width', '', 0.25, 100, finestIncrement, defaultFrontSlotWidth)
            _holsterDetailsGroup.children.addFloatSpinnerCommandInput('frontHeight', 'FrontHeight', '', 0.25, 100, finestIncrement, defaultFrontHeight)

            # Holster Appearance
            #
            _holsterAppearanceGroup = inputs.addGroupCommandInput(_commandId + '_holsterAppearanceGroup', 'Holster Appearance')
            _holsterAppearanceGroup.children.addFloatSpinnerCommandInput('backCornerRound', 'Back Corner Round', '', 0.25, 100, finestIncrement, defaultBackCornerRound)
            _holsterAppearanceGroup.children.addFloatSpinnerCommandInput('frontSlotRound', 'Slot Round', '', 0.0, 30, finestIncrement, defaultFrontSlotRound)
            _holsterAppearanceGroup.children.addFloatSpinnerCommandInput('softenFillet', 'Overall Fillet', '', 0.0, 100, 0.01, defaultSoftenFillet)

            
            # Holster Strength
            #
            _holsterStrengthGroup = inputs.addGroupCommandInput(_commandId + '_holsterStrengthGroup', 'Holster Strength')
            _holsterStrengthGroup.children.addFloatSpinnerCommandInput('sideThickness', 'Side Thickness', '', 0.25, 100, finestIncrement, defaultSideThickness)
            _holsterStrengthGroup.children.addFloatSpinnerCommandInput('backThickness', 'Back Thickness', '', 0.25, 100, finestIncrement, defaultBackThickness)
            _holsterStrengthGroup.children.addFloatSpinnerCommandInput('bottomThickness', 'Bottom Thickness', '', 0.25, 100, finestIncrement, defaultBottomThickness)
            _holsterStrengthGroup.isExpanded = False
            
            # Tolerance Group
            _toleranceGroup = inputs.addGroupCommandInput(_commandId + '_toleranceGroup', 'Tolerance Group')
            _toleranceGroup.children.addFloatSpinnerCommandInput('tolerance', 'Tolerance', '', 0.1, 10, 0.01, defaultTolerance)
            _toleranceGroup.isExpanded = False            
            
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class HolsterCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            
            unitsMgr = _app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs

            global _holsterName
            global _remoteWidth, _remoteLength, _remoteThickness
            global _frontSlotWidth, _frontHeight
            global _backCornerRound, _softenFillet, _frontSlotRound
            global _sideThickness, _backThickness, _bottomThickness
            global _tolerance         
            
            for input in inputs:
                if input.id == 'holsterName':
                    _holsterName = input.value
                elif input.id == 'remoteWidth':
                    _remoteWidth = input.value
                elif input.id == 'remoteLength':
                    _remoteLength = input.value
                elif input.id == 'remoteThickness':
                    _remoteThickness = input.value
                elif input.id == 'frontSlotWidth':
                    _frontSlotWidth = input.value
                elif input.id == 'frontHeight':
                    _frontHeight = input.value
                elif input.id == 'backCornerRound':
                    _backCornerRound = input.value
                elif input.id == 'softenFillet':
                    _softenFillet = input.value
                elif input.id == 'frontSlotRound':
                    _frontSlotRound = input.value
                elif input.id == 'sideThickness':
                    _sideThickness = input.value                
                elif input.id == 'backThickness':
                    _backThickness = input.value                
                elif input.id == 'bottomThickness':
                    _bottomThickness = input.value                
                elif input.id == 'tolerance':
                    _tolerance = input.value                
             
            args.isValidResult = True
            
            component = createComponent(_des, _holsterName.value)
            
            base_rect_profile = createBaseRectSketch(component)
            distance = createDistance((_remoteLength + _bottomThickness) * SCALE)
            
            # Extrude to full height
            #
            holster = component.features.extrudeFeatures.addSimple(base_rect_profile, distance, NEW_BODY)
            holster_body = holster.bodies.item(0)
            holster_body.name = _holsterName.value

            # Cut out the pocket
            #
            pocket_profile = createPocketSketch(component)            
            pocket_depth = createDistance(_remoteLength * SCALE * -1)
            component.features.extrudeFeatures.addSimple(pocket_profile, pocket_depth, CUT)

            # Push down the front
            #
            front_profile = createFrontSketch(component)            
            front_depth = createDistance((_remoteLength - _frontHeight) * SCALE * -1)
            component.features.extrudeFeatures.addSimple(front_profile, front_depth, CUT)

            # Create Slot
            #
            slot_profile = createSlotSketch(component)
            slot_depth = createDistance((_remoteThickness + _sideThickness) * SCALE)
            component.features.extrudeFeatures.addSimple(slot_profile, slot_depth, CUT)
            
            edges = holster_body.edges
            fillet_edges = adsk.core.ObjectCollection.create()

            # Round the back corners
            #
            if _backCornerRound > 0:
                for n in range(edges.count):
                    edge = edges.item(n)
                    if math.isclose(edge.length, _backThickness * SCALE):
                        # Need to figure out where it is
                        bb = edge.boundingBox
                        maxZ = bb.maxPoint.z
                        minZ = bb.minPoint.z
                        if math.isclose(maxZ, minZ) and math.isclose(maxZ, (_remoteLength + _bottomThickness) * SCALE):
                            fillet_edges.add(edge)

                fillets = component.features.filletFeatures
                fillet_input = fillets.createInput()
                fillet_radius = createDistance(_backCornerRound * SCALE)
                fillet_input.addConstantRadiusEdgeSet(fillet_edges, fillet_radius, True)
                fillet_input.isG2 = False
                fillet_input.isRollingBallCorner = True
                top_fillet = fillets.add(fillet_input)

            # Round the front/slot corners
            #            
            if _frontSlotRound > 0:
                fillet_edges.clear()
                for n in range(edges.count):
                    edge = edges.item(n)
                    if math.isclose(edge.length, _sideThickness * SCALE):
                        # Need to figure out where it is
                        bb = edge.boundingBox
                        maxZ = bb.maxPoint.z
                        minZ = bb.minPoint.z
                        minY = bb.minPoint.y
                    
                        if math.isclose(maxZ, minZ) and math.isclose(maxZ, (_frontHeight + _bottomThickness) * SCALE) and math.isclose(minY, 0):
                            fillet_edges.add(edge)

                fillets = component.features.filletFeatures
                fillet_input = fillets.createInput()
                fillet_radius = createDistance(_frontSlotRound * SCALE)
                fillet_input.addConstantRadiusEdgeSet(fillet_edges, fillet_radius, True)
                fillet_input.isG2 = False
                fillet_input.isRollingBallCorner = True
                top_fillet = fillets.add(fillet_input)
            
            _includeScrewHoles = True

            if _includeScrewHoles:
                # Magnet hole sketch
                screwHolesProfile = createScrewHolesSketch(component, 2)

                # Extrude for magnets
                distance = createDistance(_backThickness * SCALE)
                component.features.extrudeFeatures.addSimple(screwHolesProfile, distance, CUT)
                
                screwHolesProfile = createScrewHolesSketch(component, 4)
                distance = createDistance(_backThickness / 3 * SCALE)
                component.features.extrudeFeatures.addSimple(screwHolesProfile, distance, CUT)
                
            # Soften everything
            # 
            fillet_edges.clear()
            for n in range(edges.count):
                edge = edges.item(n)
                fillet_edges.add(edge)

            fillets = component.features.filletFeatures
            fillet_input = fillets.createInput()
            fillet_radius = createDistance(_softenFillet * SCALE)
            fillet_input.addConstantRadiusEdgeSet(fillet_edges, fillet_radius, True)
            fillet_input.isG2 = False
            fillet_input.isRollingBallCorner = True
            top_fillet = fillets.add(fillet_input)
             
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class HolsterCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
#            eventArgs = adsk.core.CommandEventArgs.cast(args)

            # when the command is done, terminate the script
            # this will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if _ui:
                _ui.messageBox('Failed in HolsterCommandDestroyHandler:\n{}'.format(traceback.format_exc()))     