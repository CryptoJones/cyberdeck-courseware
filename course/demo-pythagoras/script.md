# Section 1.1 — The Pythagorean Theorem
Demo section for Cyberdeck Courseware. Original content, public-domain topic.
Narration target ~750 words, warm UK-female register (Kokoro bf_emma).

## beat: slide:slides/01-title.html
> Welcome. In this short demo section we'll meet one of the oldest and most useful facts in all of mathematics — the Pythagorean theorem. It connects the three sides of a right triangle with a single, beautiful equation.

## beat: slide:slides/02-objectives.html
> Here's the plan. First we'll name the parts of a right triangle. Then we'll state the relationship between its sides. We'll see why that relationship is true — and it's more visual than you might expect. And finally we'll use it to find a side we don't yet know.

## beat: slide:slides/03-statement.html
> A right triangle is simply a triangle with one ninety-degree angle — a square corner. The two shorter sides that form that corner are called the legs, and we'll label them a and b. The longest side, the one sitting directly opposite the right angle, is the hypotenuse, which we'll call c. The theorem says that a squared plus b squared equals c squared.

## beat: manim:diagrams/pythagoras.py:RightTriangle
> Let's look at that triangle. The two legs, a and b, meet at the right angle. The hypotenuse, c, stretches across from one leg to the other, always opposite the square corner. Keep your eye on which side is which — that's the part people most often mix up.

## beat: slide:slides/04-square-idea.html
> Now, why is it true? The secret is that this isn't really about the lengths of the sides at all. It's about areas. Imagine building a square outward on each of the three sides. The two squares on the legs have areas a squared and b squared. The square on the hypotenuse has area c squared.

## beat: manim:diagrams/pythagoras.py:SquaresOnSides
> Watch what happens. Here are the squares on the two legs, in green and amber. And here is the much larger square on the hypotenuse. The remarkable claim is that the two smaller squares, added together, hold exactly the same amount of area as the single big one. That is the whole theorem, drawn as a picture: area a squared plus area b squared equals area c squared.

## beat: slide:slides/05-worked.html
> Let's put it to work. Suppose a right triangle has legs of length three and four, and we want the hypotenuse. We square each leg and add: three squared is nine, four squared is sixteen, and nine plus sixteen is twenty-five. The hypotenuse squared is twenty-five, so the hypotenuse itself is the square root of twenty-five, which is five.

## beat: manim:diagrams/pythagoras.py:ThreeFourFive
> There it is, step by step. Four squared plus three squared gives sixteen plus nine, which is twenty-five, and twenty-five is five squared. So the missing side, c, is exactly five. This particular triangle, with sides three, four, and five, is famous — it's the simplest right triangle whose sides are all whole numbers.

## beat: slide:slides/06-converse.html
> The theorem also runs in reverse. If you ever find three sides where a squared plus b squared equals c squared, then the triangle must be right-angled. Whole-number side sets that satisfy the equation are called Pythagorean triples — three, four, five is one, and so are five, twelve, thirteen, and eight, fifteen, seventeen. Builders still use the three, four, five trick to check that a corner is truly square.

## beat: slide:slides/07-recap.html
> So here's the one thing to carry away. For any right triangle, a squared plus b squared equals c squared, where c is the hypotenuse. And remember it's an area fact at heart: the squares on the two legs together fill the square on the hypotenuse, exactly.

## beat: slide:slides/08-references.html
> This section was written from scratch as a demonstration of the Cyberdeck Courseware pipeline — original narration, original slides, and original animated diagrams. Thanks for watching, and enjoy building your own courses.
