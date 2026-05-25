async function searchBooks(){

    let query=
        document.getElementById("query").value;

    let author=
        document.getElementById("author").value;

    let rating=
        document.getElementById("rating").value;

    let tag=
        document.getElementById("tag").value;


    let params = new URLSearchParams();

    if (query) params.append("q", query);
    if (author) params.append("author", author);
    if (rating) params.append("min_rating", rating);
    if (tag) params.append("tag", tag);

    let url=
`http://localhost:8000/books/search?${params.toString()}`;


    let response=
        await fetch(url);

    let books=
        await response.json();

    let resultsDiv=
        document.getElementById("results");

    resultsDiv.innerHTML="";


    books.forEach(book=>{

        let authors = Array.isArray(book.authors) && book.authors.length > 0
            ? book.authors.join(", ")
            : "Unknown author";

        resultsDiv.innerHTML +=
        `
        <div>

            <h3>${book.title}</h3>
            
            <p>Author: ${authors}</p>

            <p>Rating: ${book.rating}</p>

        </div>

        <hr>
        `;

    });

}
